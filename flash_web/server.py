#!/usr/bin/env python3
"""
IDM 固件刷写 Web 服务
提供 REST API + 前端页面，可接入 Moonraker 体系
"""

import base64
import hashlib
import json
import secrets
import glob
import os
import re
import socket
import struct
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import mimetypes
import fcntl
import pty
import select
import termios

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent.parent
FW_BASE = Path(os.environ.get("IDM_FW_BASE", str(SCRIPT_DIR)))
FW_DIR_IDM = FW_BASE / "IDM固件(Main firmware)"
FW_DIR_CANBOOT = FW_BASE / "Canboot通讯频率覆写用固件(canboot deployer firmware)"
FW_DIR_RP2040 = FW_BASE / "rp2040"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
LIB_DIR = Path(__file__).resolve().parent / "lib"
FLASH_TOOL_PATH = str(LIB_DIR / "flashtool.py")

def _find_klipper_env():
    """优先使用 KLIPPER_ENV 环境变量，其次探测 idm-documents 目录下的 klippy-env，
    找不到时回退全局 python3。"""
    env = os.environ.get("KLIPPER_ENV")
    if env:
        return env
    for candidate in (
        SCRIPT_DIR / "klippy-env" / "bin" / "python3",
        SCRIPT_DIR / "klippy-env" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)
    return shutil.which("python3") or "python3"


KLIPPER_ENV = _find_klipper_env()
KLIPPER_DIR = os.environ.get("KLIPPER_DIR", os.path.expanduser("~/klipper"))

HOST = "0.0.0.0"
PORT = int(os.environ.get("IDM_PORT", "8888"))

# ============================================================
# 任务管理
# ============================================================
tasks = {}
tasks_lock = threading.Lock()


class FlashTask:
    def __init__(self, task_id, params):
        self.task_id = task_id
        self.params = params
        self.status = "pending"
        self.output_lines = []
        self.created_at = datetime.now().isoformat()
        self.process = None

    def append_output(self, line):
        self.output_lines.append(line)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "status": self.status,
            "output": "\n".join(self.output_lines),
            "params": self.params,
            "created_at": self.created_at,
        }


# ============================================================
# 环境检测
# ============================================================
def detect_environment():
    info = {
        "bootloader": None,
        "flash_tool": None,
        "can_interface": None,
        "klipper_env": os.path.exists(KLIPPER_ENV),
        "has_dfutil": os.path.exists("/usr/bin/dfu-util"),
        "fw_base": str(FW_BASE.resolve()),
    }

    # 优先使用本地 lib 中的工具，回退到 klipper 路径
    if os.path.exists(FLASH_TOOL_PATH):
        info["bootloader"] = "katapult"
        info["flash_tool"] = FLASH_TOOL_PATH
    else:
        katapult_path = os.path.join(KLIPPER_DIR, "lib/katapult/flashtool.py")
        if os.path.exists(katapult_path):
            info["bootloader"] = "katapult"
            info["flash_tool"] = katapult_path

    try:
        result = subprocess.run(
            ["ip", "-o", "link", "show"], capture_output=True, text=True, timeout=5
        )
        match = re.search(r"can\d+", result.stdout)
        if match:
            info["can_interface"] = match.group(0)
    except Exception:
        pass

    return info


# ============================================================
# 设备查询
# ============================================================
def _is_bl_device(path):
    name = path.lower()
    return "katapult" in name or "canboot" in name


def _scan_serial_devices():
    devices = set()
    for pattern in ["/dev/serial/by-id/*", "/dev/ttyUSB*", "/dev/ttyACM*"]:
        devices.update(glob.glob(pattern))
    return devices


def query_can_devices():
    env = detect_environment()
    can_if = env["can_interface"] or "can0"

    can_response = moonraker_request(
        "/machine/peripherals/canbus?" + urlencode({"interface": can_if})
    )
    can_result = can_response.get("result", can_response)
    unassigned = can_result.get("can_uuids", []) if "error" not in can_response else []
    device_rows = [
        {
            "name": "",
            "uuid": device.get("uuid", "").lower(),
            "application": device.get("application", "Unknown"),
            "mcu_model": "",
            "source": "unassigned",
        }
        for device in unassigned
    ]

    config_response = moonraker_request("/printer/objects/query?configfile")
    objects_response = moonraker_request("/printer/objects/list")
    config_result = config_response.get("result", config_response)
    objects_result = objects_response.get("result", objects_response)
    configfile = config_result.get("status", {}).get("configfile", {})
    config = configfile.get("settings", configfile.get("config", {}))
    mcu_objects = [
        name for name in objects_result.get("objects", [])
        if name == "mcu" or name.startswith("mcu ")
    ]
    status_response = moonraker_request(
        "/printer/objects/query?" + urlencode({name: "" for name in mcu_objects})
    ) if mcu_objects else {}
    statuses = status_response.get("result", status_response).get("status", {})

    for mcu_name in mcu_objects:
        short_name = mcu_name[4:] if mcu_name.startswith("mcu ") else ""
        settings = config.get(mcu_name, config.get(short_name, {}))
        status = statuses.get(mcu_name, {})
        constants = status.get("mcu_constants", {})
        if not constants and not status.get("mcu_version"):
            continue
        model = next((str(constants[key]) for key in (
            "MCU", "MCU_TYPE", "CONFIG_MCU", "CHIP", "CHIP_TYPE"
        ) if constants.get(key)), "")
        device_rows.append({
            "name": short_name or "mcu",
            "uuid": str(settings.get("canbus_uuid", "")).lower(),
            "application": "Klipper",
            "mcu_model": model,
            "source": "runtime",
            "mcu_version": status.get("mcu_version", ""),
        })

    merged_devices = []
    by_uuid = {}
    for device in device_rows:
        uuid = device["uuid"]
        if not uuid:
            merged_devices.append(device)
            continue
        existing = by_uuid.get(uuid)
        if existing is None:
            by_uuid[uuid] = device
            merged_devices.append(device)
            continue
        if existing["source"] == "unassigned" and device["source"] == "runtime":
            existing.update({
                "name": device["name"],
                "mcu_model": device["mcu_model"],
                "mcu_version": device["mcu_version"],
                "in_use": True,
            })
        elif existing["source"] == "runtime" and device["source"] == "unassigned":
            device.update({
                "name": existing["name"],
                "mcu_model": existing["mcu_model"],
                "mcu_version": existing["mcu_version"],
                "in_use": True,
            })
            by_uuid[uuid] = device
            merged_devices[merged_devices.index(existing)] = device

    for device in merged_devices:
        device.setdefault("in_use", device["source"] == "runtime")

    direct_status = {}
    for device in merged_devices:
        if (
            device["source"] != "unassigned"
            or device["application"].lower() != "katapult"
            or device["name"]
            or device["mcu_model"]
        ):
            continue
        status, output = query_katapult_status(env, can_if, device["uuid"])
        direct_status[device["uuid"]] = output
        device.update(status)

    katapult_uuids = sorted({
        device["uuid"] for device in merged_devices
        if device["application"].lower() == "katapult" and device["uuid"]
    })
    klipper_uuids = sorted({
        device["uuid"] for device in merged_devices
        if device["application"].lower() == "klipper" and device["uuid"]
    })
    raw_output = json.dumps({
        "canbus": can_response,
        "canbus_error": can_response.get("error", ""),
        "configfile": config_response,
        "mcu_objects": objects_response,
        "mcu_status": status_response,
        "direct_status": direct_status,
    }, ensure_ascii=False, indent=2)
    return {
        "devices": katapult_uuids,
        "katapult_uuids": katapult_uuids,
        "klipper_uuids": klipper_uuids,
        "can_devices": merged_devices,
        "raw_output": raw_output,
        "can_interface": can_if,
    }


def query_katapult_status(env, can_if, can_uuid):
    flash_tool = env.get("flash_tool")
    if not flash_tool:
        return {}, "Katapult status query skipped: flash tool unavailable"
    python_exe = KLIPPER_ENV if os.path.exists(KLIPPER_ENV) else sys.executable
    cmd = [python_exe, flash_tool, "-i", can_if, "-u", can_uuid, "-s"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = "$ " + " ".join(cmd) + "\n" + result.stdout + result.stderr
    except Exception as error:
        return {}, f"Katapult status query failed: {error}"

    model = re.search(r"MCU type:\s*(.+)", output)
    version = re.search(r"Software Version:\s*(.+)", output)
    return {
        "name": "Katapult",
        "mcu_model": model.group(1).strip() if model else "",
        "mcu_version": version.group(1).strip() if version else "",
    }, output


def query_usb_devices():
    devices = sorted(_scan_serial_devices())
    devices = [d for d in devices if "idm" in d.lower()]
    return {"devices": devices}


def detect_bootloader_serial(serial_device, try_enter=True):
    """Detect bootloader serial. try_enter=True enters bootloader first.
    try_enter=False only scans existing devices without entering BL."""
    if _is_bl_device(serial_device) and os.path.exists(serial_device):
        return serial_device

    if not try_enter:
        for d in sorted(_scan_serial_devices()):
            if _is_bl_device(d):
                return d
        return ""

    before = _scan_serial_devices()

    enter_cmd = [
        KLIPPER_ENV,
        "-c",
        f"import flash_usb as u; u.enter_bootloader('{serial_device}')",
    ]
    try:
        subprocess.run(enter_cmd, cwd=LIB_DIR, capture_output=True, timeout=15)
        time.sleep(3)
    except Exception:
        pass

    new_devices = _scan_serial_devices() - before
    for d in sorted(new_devices):
        if _is_bl_device(d):
            return d

    for d in sorted(new_devices):
        return d

    candidate = serial_device
    if os.path.exists(serial_device):
        return candidate
    for d in sorted(_scan_serial_devices() - before):
        if d != serial_device:
            return d
    return candidate


def _run_dfutil(args, timeout=300):
    for try_sudo in [False, True]:
        cmd = (["sudo", "-n"] if try_sudo else []) + ["dfu-util"] + args
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                return result
            if try_sudo:
                return result
        except Exception:
            if try_sudo:
                raise
    return None


def query_dfu_devices():
    try:
        result = _run_dfutil(["-l"], timeout=10)
        if result is None:
            return {"error": "dfu-util not available", "devices_found": False}
        output = result.stdout + result.stderr
        return {"raw_output": output, "devices_found": "Found" in output}
    except Exception as e:
        return {"error": str(e), "devices_found": False}


# ============================================================
# 固件列表
# ============================================================
def _scan_firmware_dir(base_dir, is_deployer=False, is_rp2040=False):
    versions = []
    if not base_dir.exists():
        return versions

    current_files = []
    for f in base_dir.iterdir():
        if f.is_file() and f.suffix in (".bin", ".uf2"):
            if is_rp2040:
                is_dep = "deployer" in f.name.lower() or "canboot_" in f.name.lower()
                is_main = "idm_" in f.name.lower() or "IDM_" in f.name
                if is_deployer and not is_dep:
                    continue
                if not is_deployer and not is_main:
                    continue
            current_files.append({"name": f.name, "path": str(f)})

    if current_files:
        versions.append(
            {"label": "最新版", "files": sorted(current_files, key=lambda x: x["name"])}
        )

    old_dir = base_dir / "old"
    if old_dir.exists() and old_dir.is_dir():
        for version_dir in sorted(old_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                ver_files = []
                for f in version_dir.rglob("*"):
                    if f.is_file() and f.suffix in (".bin", ".uf2"):
                        if is_rp2040:
                            is_dep = (
                                "deployer" in f.name.lower()
                                or "canboot_" in f.name.lower()
                            )
                            is_main = "idm_" in f.name.lower() or "IDM_" in f.name
                            if is_deployer and not is_dep:
                                continue
                            if not is_deployer and not is_main:
                                continue
                        ver_files.append({"name": f.name, "path": str(f)})
                if ver_files:
                    versions.append(
                        {
                            "label": version_dir.name,
                            "files": sorted(ver_files, key=lambda x: x["name"]),
                        }
                    )

    return versions


def list_firmware(fw_base=None):
    if fw_base:
        base = Path(fw_base)
    else:
        base = FW_BASE
    fw_idm = base / "IDM固件(Main firmware)"
    fw_canboot = base / "Canboot通讯频率覆写用固件(canboot deployer firmware)"
    fw_rp2040 = base / "rp2040"
    return {
        "stm32": {
            "main": _scan_firmware_dir(fw_idm),
            "deployer": _scan_firmware_dir(fw_canboot, is_deployer=True),
        },
        "rp2040": {
            "main": _scan_firmware_dir(fw_rp2040, is_rp2040=True),
            "deployer": _scan_firmware_dir(fw_rp2040, is_deployer=True, is_rp2040=True),
        },
    }


# ============================================================
# 后端多语言 (从 i18n/ 目录加载，与前端共用翻译文件)
# ============================================================
I18N_DIR = Path(__file__).resolve().parent / "i18n"
_BACKEND_CACHE = {}


def _load_i18n(lang):
    if lang in _BACKEND_CACHE:
        return _BACKEND_CACHE[lang]
    try:
        path = I18N_DIR / f"{lang}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            backend_msgs = data.get("_backend", {})
            _BACKEND_CACHE[lang] = backend_msgs
            return backend_msgs
    except Exception:
        pass
    _BACKEND_CACHE[lang] = {}
    return {}


def _t(lang, key, **kwargs):
    msgs = _load_i18n(lang) or _load_i18n("zh") or _load_i18n("en")
    s = msgs.get(key, key)
    if kwargs:
        s = s.format(**kwargs)
    return s


# ============================================================
# Katapult 协议
# ============================================================
KATAPULT_HEADER = b"\x01\x88"
KATAPULT_TRAILER = b"\x99\x03"


def crc16_ccitt(buf):
    crc = 0xFFFF
    for b in buf:
        b ^= crc & 0xFF
        b ^= (b & 0x0F) << 4
        crc = ((b << 8) | (crc >> 8)) ^ (b >> 4) ^ (b << 3)
    return crc & 0xFFFF


def build_katapult_cmd(cmd, payload=b""):
    wcnt = (len(payload) // 4) & 0xFF
    out = bytearray(KATAPULT_HEADER)
    out.append(cmd)
    out.append(wcnt)
    out.extend(payload)
    crc_val = crc16_ccitt(out[2:])
    out.extend(struct.pack("<H", crc_val))
    out.extend(KATAPULT_TRAILER)
    return bytes(out)


# ============================================================
# CAN 传输层 (Linux socket CAN)
# ============================================================
CAN_FRAME_FMT = "<IB3x8s"
CAN_ADMIN_ID = 0x3F0
CAN_ADMIN_RESP_ID = 0x3F1
CAN_NODEID_OFFSET = 128


def _can_open(interface):
    sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    sock.bind((interface,))
    return sock


def _can_send(sock, can_id, data):
    payload_len = min(len(data), 8)
    padded = data[:8].ljust(8, b"\x00")
    sock.send(struct.pack(CAN_FRAME_FMT, can_id, payload_len, padded))


def _can_recv(sock, timeout=3):
    sock.settimeout(timeout)
    try:
        data = sock.recv(16)
        can_id, length, pkt = struct.unpack(CAN_FRAME_FMT, data)
        return can_id & 0x1FFFFFFF, pkt[:length]
    except socket.timeout:
        return None, None


def _can_exit_bootloader(can_interface, can_uuid):
    """通过 CAN 发送 COMPLETE 命令退出 bootloader"""
    uuid_bytes = bytes.fromhex(can_uuid)[:6]

    sock = _can_open(can_interface)

    # 1. 重置所有节点 ID
    _can_send(sock, CAN_ADMIN_ID, bytes([0x12]))
    time.sleep(0.1)

    # 2. 分配节点 ID
    node_id = CAN_NODEID_OFFSET
    _can_send(sock, CAN_ADMIN_ID, bytes([0x11]) + uuid_bytes + bytes([node_id]))
    time.sleep(0.3)

    # 3. 发送 CONNECT
    node_tx_id = node_id * 2 + 0x100
    _can_send(sock, node_tx_id, build_katapult_cmd(0x11))
    # 等待响应
    deadline = time.time() + 3
    while time.time() < deadline:
        can_id, _ = _can_recv(sock, timeout=0.5)
        if can_id is not None:
            break
        time.sleep(0.05)

    # 4. 发送 COMPLETE
    _can_send(sock, node_tx_id, build_katapult_cmd(0x15))
    time.sleep(0.3)
    try:
        sock.close()
    except Exception:
        pass


def _read_json_body(handler):
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length == 0:
        raise ValueError("empty body")
    body = handler.rfile.read(content_length)
    return json.loads(body)


# ============================================================
# 刷写执行
# ============================================================
def run_flash(task):
    task.status = "running"
    params = task.params

    fw_file = params.get("fw_file", "")
    mode = params.get("mode", "CAN")
    bootloader = params.get("bootloader", "katapult")
    can_interface = params.get("can_interface", "can0")
    can_uuid = params.get("can_uuid", "")
    serial_device = params.get("serial_device", "")
    dfu_addr = params.get("dfu_addr", "0x8002000")
    lang = params.get("lang", "zh")

    def log(msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        task.append_output(line)

    log(_t(lang, "flash_start", file=os.path.basename(fw_file)))
    log(_t(lang, "flash_mode", mode=mode, bl=bootloader))

    env = detect_environment()
    flash_tool = env.get("flash_tool", "")
    python_exe = KLIPPER_ENV if os.path.exists(KLIPPER_ENV) else sys.executable

    if not flash_tool and mode != "DFU":
        task.status = "failed"
        log(_t(lang, "err_no_tool"))
        return

    try:
        if mode == "CAN":
            if not can_uuid:
                task.status = "failed"
                log(_t(lang, "err_no_uuid"))
                return

            cmd = [python_exe, flash_tool, "-i", can_interface, "-f", fw_file, "-u", can_uuid]

        elif mode == "USB":
            bootloader_serial = params.get("bootloader_serial", "")
            if bootloader_serial and os.path.exists(bootloader_serial):
                log(_t(lang, "bl_already", device=bootloader_serial))
            elif bootloader_serial:
                log(f"BL device gone: {bootloader_serial}, try re-enter BL")
                if not serial_device:
                    task.status = "failed"
                    log("请先点击「进入BL」使设备进入Bootloader模式")
                    return
                log(_t(lang, "enter_bl", device=serial_device))
                bootloader_serial = detect_bootloader_serial(serial_device, try_enter=True)
            else:
                if not serial_device:
                    task.status = "failed"
                    log(_t(lang, "err_no_serial"))
                    return
                log(_t(lang, "enter_bl", device=serial_device))
                bootloader_serial = detect_bootloader_serial(serial_device, try_enter=True)

            cmd = [python_exe, flash_tool, "-d", bootloader_serial, "-f", fw_file]

        elif mode == "DFU":
            dfu_args = [
                "-d",
                ",0483:df11",
                "-R",
                "-a",
                "0",
                "-s",
                f"{dfu_addr}:leave",
                "-D",
                fw_file,
            ]
            cmd = ["dfu-util"] + dfu_args
            sudo_cmd = ["sudo", "-n", "dfu-util"] + dfu_args

        else:
            task.status = "failed"
            log(_t(lang, "err_unknown_mode", mode=mode))
            return

        log(_t(lang, "exec_cmd", cmd=" ".join(cmd)))

        def _run(c):
            process = subprocess.Popen(
                c,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            task.process = process
            for line in iter(process.stdout.readline, ""):
                line = line.rstrip()
                if line:
                    task.append_output(line)
            process.wait()
            return process.returncode

        rc = _run(cmd)

        if mode == "DFU" and rc != 0:
            log(_t(lang, "retry_sudo", cmd=" ".join(sudo_cmd)))
            rc = _run(sudo_cmd)

        if rc == 0:
            task.status = "completed"
            log(_t(lang, "flash_done"))
        else:
            task.status = "failed"
            log(_t(lang, "flash_fail", code=str(rc)))

    except subprocess.TimeoutExpired:
        task.status = "failed"
        log(_t(lang, "err_timeout"))
    except Exception as e:
        task.status = "failed"
        log(f"Error: {str(e)}")


# ============================================================
# Moonraker 代理
# ============================================================
MOONRAKER_URL = os.environ.get("MOONRAKER_URL", "http://localhost:7125")


def moonraker_request(endpoint):
    import urllib.request
    import urllib.error

    try:
        url = f"{MOONRAKER_URL}{endpoint}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# WebSocket / Web Terminal
# 纯标准库实现 RFC 6455，前端使用 xterm.js
# 安全：进入终端需用系统用户密码登录（PAM 验证，回退 su），
# 登录成功签发带时效 token，ws 连接必须携带有效 token。
# 仅当 IDM_TERMINAL != "0" 时启用
# ============================================================
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# 终端登录 token
TERMINAL_TOKENS = {}
TERMINAL_TOKENS_LOCK = threading.Lock()
TERMINAL_TOKEN_TTL = 24 * 3600

# 登录失败限速
LOGIN_ATTEMPTS = {}
LOGIN_LOCK = threading.Lock()
LOGIN_MAX_ATTEMPTS = 30
LOGIN_WINDOW = 300  # 5 分钟
LOGIN_BASE_DELAY = 0.5


def terminal_enabled():
    return os.environ.get("IDM_TERMINAL", "1") != "0"


def pam_authenticate(username, password):
    """通过 PAM 验证系统用户密码（无需 root，依赖 unix_chkpwd）。
    返回 True/False；PAM 不可用时返回 None。"""
    try:
        import ctypes
        import ctypes.util
    except ImportError:
        return None

    pam_lib = ctypes.util.find_library("pam") or ctypes.util.find_library("libpam")
    if not pam_lib:
        return None
    try:
        libpam = ctypes.CDLL(pam_lib)
    except OSError:
        return None

    PAM_SUCCESS = 0
    PAM_PROMPT_ECHO_OFF = 1

    class pam_message_t(ctypes.Structure):
        _fields_ = [("msg_style", ctypes.c_int), ("msg", ctypes.c_char_p)]

    class pam_response_t(ctypes.Structure):
        _fields_ = [("resp", ctypes.c_char_p), ("resp_retcode", ctypes.c_int)]

    PAM_CONV_FUNC = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.POINTER(pam_message_t)),
        ctypes.POINTER(ctypes.POINTER(pam_response_t)),
        ctypes.c_void_p,
    )

    class pam_conv_t(ctypes.Structure):
        _fields_ = [("conv", PAM_CONV_FUNC), ("appdata_ptr", ctypes.c_void_p)]

    libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
    libc.malloc.restype = ctypes.c_void_p
    libc.malloc.argtypes = [ctypes.c_size_t]
    libc.free.restype = None
    libc.free.argtypes = [ctypes.c_void_p]

    # PAM 会用 libc free() 释放响应数组和字符串，因此必须用 malloc 分配，
    # 不能用 Python 管理的 ctypes buffer（会导致 free(): invalid pointer）。
    password_buf = password.encode("utf-8") + b"\x00"
    password_ptr = libc.malloc(len(password_buf))
    if not password_ptr:
        return None
    ctypes.memmove(password_ptr, password_buf, len(password_buf))

    def conv_callback(num_msg, msg, resp, appdata_ptr):
        n = num_msg
        array_mem = libc.malloc(ctypes.sizeof(pam_response_t) * n)
        if not array_mem:
            return 2  # PAM_BUF_ERR
        arr = (pam_response_t * n).from_address(array_mem)
        for i in range(n):
            style = msg[i][0].msg_style
            if style == PAM_PROMPT_ECHO_OFF:
                arr[i].resp = ctypes.c_char_p(password_ptr)
            else:
                empty_ptr = libc.malloc(1)
                if empty_ptr:
                    ctypes.memset(empty_ptr, 0, 1)
                    arr[i].resp = ctypes.c_char_p(empty_ptr)
            arr[i].resp_retcode = 0
        resp[0] = ctypes.cast(array_mem, ctypes.POINTER(pam_response_t))
        return PAM_SUCCESS

    conv_func = PAM_CONV_FUNC(conv_callback)
    conv = pam_conv_t(conv_func, None)
    handle = ctypes.c_void_p()

    pam_start = libpam.pam_start
    pam_start.restype = ctypes.c_int
    pam_start.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.POINTER(pam_conv_t),
        ctypes.POINTER(ctypes.c_void_p),
    ]

    for service in (b"login", b"system-auth", b"other"):
        rc = pam_start(
            service, username.encode("utf-8"), ctypes.byref(conv), ctypes.byref(handle)
        )
        if rc == PAM_SUCCESS:
            break
    else:
        return False

    try:
        pam_auth = libpam.pam_authenticate
        pam_auth.restype = ctypes.c_int
        pam_auth.argtypes = [ctypes.c_void_p, ctypes.c_int]
        rc = pam_auth(handle, 0)
    finally:
        try:
            pam_end = libpam.pam_end
            pam_end.restype = ctypes.c_int
            pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
            pam_end(handle, rc)
        except Exception:
            pass

    return rc == PAM_SUCCESS


def su_authenticate(username, password):
    """通过 su 验证系统密码（PAM 不可用时的回退）。
    返回 True/False；su 不可用时返回 None。"""
    if not shutil.which("su"):
        return None
    try:
        master_fd, slave_fd = pty.openpty()
    except OSError:
        return None
    try:
        proc = subprocess.Popen(
            ["su", "-", username, "-c", "true"],
            stdin=slave_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
    finally:
        os.close(slave_fd)
    try:
        # 等待密码提示后写入
        deadline = time.time() + 5
        prompt = b""
        while time.time() < deadline:
            rlist, _, _ = select.select([master_fd], [], [], 0.2)
            if rlist:
                try:
                    chunk = os.read(master_fd, 1024)
                except OSError:
                    break
                if not chunk:
                    break
                prompt += chunk
                if b"assword" in prompt or b"\n" in prompt:
                    break
        try:
            os.write(master_fd, password.encode("utf-8") + b"\n")
        except OSError:
            return False
        try:
            proc.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            return False
        return proc.returncode == 0
    except OSError:
        return False
    finally:
        try:
            os.close(master_fd)
        except Exception:
            pass


def verify_system_password(username, password):
    """验证系统用户密码。返回 True/False；无法验证(无 PAM 且无 su)返回 None。"""
    result = pam_authenticate(username, password)
    if result is not None:
        return result
    result = su_authenticate(username, password)
    if result is not None:
        return result
    return None


def _issue_terminal_token(username):
    token = secrets.token_urlsafe(32)
    with TERMINAL_TOKENS_LOCK:
        TERMINAL_TOKENS[token] = (username, time.time() + TERMINAL_TOKEN_TTL)
    return token


def _check_terminal_token(token):
    if not token:
        return None
    with TERMINAL_TOKENS_LOCK:
        entry = TERMINAL_TOKENS.get(token)
        if not entry:
            return None
        user, expiry = entry
        if time.time() > expiry:
            del TERMINAL_TOKENS[token]
            return None
        return user


def _login_record(username, success):
    """记录登录尝试并返回限速延迟秒数。"""
    with LOGIN_LOCK:
        now = time.time()
        info = LOGIN_ATTEMPTS.get(username, {"count": 0, "last": 0})
        if now - info["last"] > LOGIN_WINDOW:
            info = {"count": 0, "last": now}
        if success:
            LOGIN_ATTEMPTS.pop(username, None)
            return 0.0
        info["count"] += 1
        info["last"] = now
        LOGIN_ATTEMPTS[username] = info
        return min(LOGIN_BASE_DELAY * (info["count"] - 1), 5.0)


def _login_blocked(username):
    with LOGIN_LOCK:
        info = LOGIN_ATTEMPTS.get(username, {})
        now = time.time()
        if now - info.get("last", 0) > LOGIN_WINDOW:
            return False
        return info.get("count", 0) >= LOGIN_MAX_ATTEMPTS


def _ws_accept_key(sec_websocket_key):
    return base64.b64encode(
        hashlib.sha1((sec_websocket_key + WS_GUID).encode("utf-8")).digest()
    ).decode("ascii")


def _recv_exact(conn, n):
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def _ws_encode_frame(payload, opcode=0x1):
    frame = bytearray([0x80 | opcode])
    length = len(payload)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack(">Q", length))
    frame.extend(payload)
    return bytes(frame)


def _ws_decode_frame(conn):
    header = _recv_exact(conn, 2)
    if header is None:
        return None
    opcode = header[0] & 0x0F
    masked = header[1] & 0x80
    length = header[1] & 0x7F
    if length == 126:
        ext = _recv_exact(conn, 2)
        if ext is None:
            return None
        length = struct.unpack(">H", ext)[0]
    elif length == 127:
        ext = _recv_exact(conn, 8)
        if ext is None:
            return None
        length = struct.unpack(">Q", ext)[0]
    if masked:
        mask = _recv_exact(conn, 4)
        if mask is None:
            return None
    else:
        mask = None
    payload = _recv_exact(conn, length) or b""
    if mask:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return {"opcode": opcode, "payload": payload}


def _handle_pty_input(master_fd, payload):
    """处理发往 pty 的输入。resize 控制消息（\x00RSZ cols rows）调整终端尺寸，
    返回 True；普通输入直接写入，返回 False。"""
    if payload.startswith(b"\x00RSZ "):
        try:
            _, spec = payload.split(b" ", 1)
            cols_s, rows_s = spec.split()
            cols, rows = int(cols_s), int(rows_s)
            fcntl.ioctl(
                master_fd,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", rows, cols, 0, 0),
            )
        except (ValueError, OSError):
            pass
        return True
    return False


def _run_terminal(handler):
    """处理 WebSocket 升级并转发 PTY 数据。handler 为 FlashAPIHandler 实例。"""
    conn = handler.connection
    key = handler.headers.get("Sec-WebSocket-Key")
    if not key:
        handler.send_json({"error": "websocket upgrade required"}, 400)
        return

    accept = _ws_accept_key(key)
    handler.protocol_version = "HTTP/1.1"
    handler.send_response(101, "Switching Protocols")
    handler.send_header("Upgrade", "websocket")
    handler.send_header("Connection", "Upgrade")
    handler.send_header("Sec-WebSocket-Accept", accept)
    handler.end_headers()
    handler.close_connection = True

    shell = os.environ.get("SHELL") or "/bin/bash"
    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            [shell],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            start_new_session=True,
        )
    finally:
        os.close(slave_fd)

    try:
        conn.settimeout(0.2)
        while True:
            try:
                frame = _ws_decode_frame(conn)
            except socket.timeout:
                frame = None
            except (OSError, ConnectionError):
                break

            if frame is not None:
                opcode = frame["opcode"]
                payload = frame["payload"]
                if opcode == 0x8:  # close
                    try:
                        conn.sendall(_ws_encode_frame(payload or b"", opcode=0x8))
                    except OSError:
                        pass
                    break
                elif opcode == 0x9:  # ping
                    try:
                        conn.sendall(_ws_encode_frame(payload, opcode=0xA))
                    except OSError:
                        break
                elif opcode == 0x1:  # text
                    if _handle_pty_input(master_fd, payload):
                        continue
                    try:
                        os.write(master_fd, payload)
                    except OSError:
                        break

            if proc.poll() is not None:
                break

            try:
                rlist, _, _ = select.select([master_fd], [], [], 0.05)
                if rlist:
                    try:
                        data = os.read(master_fd, 4096)
                    except OSError:
                        data = b""
                    if not data:
                        break
                    try:
                        conn.sendall(_ws_encode_frame(data, opcode=0x1))
                    except OSError:
                        break
            except (OSError, ValueError):
                break
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            os.close(master_fd)
        except Exception:
            pass


# ============================================================
# HTTP 路由处理
# ============================================================
class FlashAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(TEMPLATES_DIR), **kwargs)

    def log_message(self, format, *args):
        pass

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API 路由
        if path == "/api/env":
            self.send_json(detect_environment())

        elif path == "/api/terminal/ws":
            if not terminal_enabled():
                self.send_json({"error": "terminal disabled"}, 403)
                return
            qs = parse_qs(parsed.query)
            token = qs.get("token", [""])[0]
            if not _check_terminal_token(token):
                self.send_json({"error": "unauthorized"}, 401)
                return
            _run_terminal(self)

        elif path == "/api/terminal/status":
            qs = parse_qs(parsed.query)
            token = qs.get("token", [""])[0]
            self.send_json(
                {
                    "enabled": terminal_enabled(),
                    "authenticated": bool(_check_terminal_token(token)),
                }
            )

        elif path == "/api/devices/can":
            self.send_json(query_can_devices())

        elif path == "/api/devices/usb":
            self.send_json(query_usb_devices())

        elif path == "/api/devices/usb/bootloader":
            qs = parse_qs(parsed.query)
            serial = qs.get("serial", [""])[0]
            bl = detect_bootloader_serial(serial, try_enter=False)
            self.send_json({"bootloader_serial": bl})

        elif path == "/api/devices/dfu":
            self.send_json(query_dfu_devices())

        elif path == "/api/firmware/list":
            qs = parse_qs(parsed.query)
            fw_base = qs.get("fw_base", [None])[0]
            self.send_json(list_firmware(fw_base))

        elif path == "/api/tasks":
            with tasks_lock:
                self.send_json([t.to_dict() for t in tasks.values()])

        elif path.startswith("/api/tasks/") and path.endswith("/output"):
            task_id = path.split("/")[3]
            with tasks_lock:
                task = tasks.get(task_id)
            if task:
                self.send_json(task.to_dict())
            else:
                self.send_json({"error": "task not found"}, 404)

        elif path == "/api/moonraker/info":
            self.send_json(moonraker_request("/server/info"))

        elif path == "/api/moonraker/printer":
            self.send_json(
                moonraker_request("/printer/objects/query?toolhead&heater_bed&extruder")
            )

        # 静态文件
        elif path.startswith("/i18n/"):
            lang_file = path.split("/")[-1]
            lang_path = I18N_DIR / lang_file
            if lang_path.exists() and lang_path.suffix == ".json":
                self.send_json(json.loads(lang_path.read_text(encoding="utf-8")))
            else:
                self.send_json({"error": "not found"}, 404)

        elif path == "/" or path == "/index.html":
            html_path = TEMPLATES_DIR / "index.html"
            if html_path.exists():
                self.send_html(html_path.read_text(encoding="utf-8"))
            else:
                self.send_json({"error": "index.html not found"}, 404)

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            body_data = _read_json_body(self) if path != "/api/flash" else {}
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "invalid JSON body"}, 400)
            return

        if path == "/api/terminal/auth":
            if not terminal_enabled():
                self.send_json({"error": "terminal disabled"}, 403)
                return
            username = body_data.get("username", "").strip()
            password = body_data.get("password", "")
            if not username or not isinstance(password, str):
                self.send_json({"error": "username and password required"}, 400)
                return
            if "/" in username or "\x00" in username:
                self.send_json({"error": "invalid username"}, 400)
                return
            if _login_blocked(username):
                self.send_json({"error": "too many attempts, try again later"}, 429)
                return
            delay = _login_record(username, success=False)
            if delay > 0:
                time.sleep(delay)
            result = verify_system_password(username, password)
            if result is None:
                self.send_json(
                    {
                        "error": "authentication unavailable: PAM and su are both missing on this system"
                    },
                    503,
                )
                return
            if result:
                _login_record(username, success=True)
                token = _issue_terminal_token(username)
                self.send_json(
                    {"ok": True, "token": token, "username": username},
                )
            else:
                self.send_json({"error": "invalid username or password"}, 401)

        elif path == "/api/flash":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            params = json.loads(body)

            task_id = uuid.uuid4().hex[:12]
            task = FlashTask(task_id, params)

            with tasks_lock:
                tasks[task_id] = task

            t = threading.Thread(target=run_flash, args=(task,), daemon=True)
            t.start()

            self.send_json({"task_id": task_id})

        elif path == "/api/flash/cancel":
            task_id = body_data.get("task_id")

            with tasks_lock:
                task = tasks.get(task_id)
            if task and task.process:
                task.process.terminate()
                task.status = "cancelled"
                lang = task.params.get("lang", "zh")
                task.append_output(_t(lang, "cancelled"))
                self.send_json({"status": "cancelled"})
            else:
                self.send_json({"error": "task not running"}, 404)

        elif path == "/api/devices/usb/enter-bl":
            serial = body_data.get("serial_device", "")
            if not serial:
                self.send_json(
                    {"success": False, "error": "missing serial_device"}, 400
                )
                return
            try:
                cmd = [
                    KLIPPER_ENV,
                    "-c",
                    f"import flash_usb as u; u.enter_bootloader('{serial}')",
                ]
                subprocess.run(cmd, cwd=LIB_DIR, capture_output=True, timeout=15)
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})

        elif path == "/api/devices/usb/exit-bl":
            serial = body_data.get("serial_device", "")
            if not serial:
                self.send_json(
                    {"success": False, "error": "missing serial_device"}, 400
                )
                return
            try:
                import serial as pyserial

                s = pyserial.Serial(baudrate=250000, timeout=0, exclusive=True)
                s.port = serial
                s.open()
                s.reset_input_buffer()
                s.write(build_katapult_cmd(0x90))
                s.flush()
                time.sleep(0.3)
                s.reset_input_buffer()
                s.write(build_katapult_cmd(0x11))
                s.flush()
                raw = b""
                deadline = time.time() + 3
                while time.time() < deadline:
                    chunk = s.read(4096)
                    if chunk:
                        raw += chunk
                        if KATAPULT_TRAILER in raw and raw.find(KATAPULT_HEADER) >= 0:
                            break
                    time.sleep(0.05)
                s.write(build_katapult_cmd(0x15))
                s.flush()
                time.sleep(0.3)
                try:
                    s.close()
                except Exception:
                    pass
                time.sleep(1)
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})

        elif path == "/api/devices/can/enter-bl":
            can_interface = body_data.get("can_interface", "can0")
            can_uuid = body_data.get("can_uuid", "")
            if not can_uuid:
                self.send_json({"success": False, "error": "missing can_uuid"}, 400)
                return
            try:
                uuid_bytes = bytes.fromhex(can_uuid)
                if len(uuid_bytes) >= 6:
                    uuid_bytes = uuid_bytes[:6]
                sock = _can_open(can_interface)
                _can_send(sock, CAN_ADMIN_ID, bytes([0x02]) + uuid_bytes)
                try:
                    sock.close()
                except Exception:
                    pass
                time.sleep(2)
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})

        elif path == "/api/devices/can/exit-bl":
            can_interface = body_data.get("can_interface", "can0")
            can_uuid = body_data.get("can_uuid", "")
            if not can_uuid:
                self.send_json({"success": False, "error": "missing can_uuid"}, 400)
                return
            try:
                _can_exit_bootloader(can_interface, can_uuid)
                time.sleep(1)
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})

        else:
            self.send_json({"error": "not found"}, 404)


# ============================================================
# 主入口
# ============================================================
def main():
    os.chdir(str(TEMPLATES_DIR))
    server = ThreadingHTTPServer((HOST, PORT), FlashAPIHandler)
    print(f"\n  IDM Flash Web 服务已启动")
    print(f"  地址: http://localhost:{PORT}")
    print(f"  Moonraker: {MOONRAKER_URL}")
    print(f"  终端: {'已启用' if terminal_enabled() else '已禁用(IDM_TERMINAL=0)'}")
    print(f"  按 Ctrl+C 停止\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()

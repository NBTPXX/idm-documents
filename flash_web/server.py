#!/usr/bin/env python3
"""
IDM 固件刷写 Web 服务
提供 REST API + 前端页面，可接入 Moonraker 体系
"""

import json
import glob
import os
import re
import socket
import struct
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import mimetypes

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent.parent
FW_BASE = Path(os.environ.get("IDM_FW_BASE", str(SCRIPT_DIR)))
FW_DIR_IDM = FW_BASE / "IDM固件(Main firmware)"
FW_DIR_CANBOOT = FW_BASE / "Canboot通讯频率覆写用固件(canboot deployer firmware)"
FW_DIR_RP2040 = FW_BASE / "rp2040"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

KLIPPER_ENV = os.path.expanduser("~/klippy-env/bin/python")
KLIPPER_DIR = os.path.expanduser("~/klipper")

HOST = "0.0.0.0"
PORT = 8888

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

    katapult_path = os.path.join(KLIPPER_DIR, "lib/katapult/flashtool.py")
    canboot_path = os.path.join(KLIPPER_DIR, "lib/canboot/flash_can.py")

    if os.path.exists(katapult_path):
        info["bootloader"] = "katapult"
        info["flash_tool"] = katapult_path
    elif os.path.exists(canboot_path):
        info["bootloader"] = "canboot"
        info["flash_tool"] = canboot_path

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
    return "katapult" in name or "canboot" in name or "stm32" in name


def _scan_serial_devices():
    devices = set()
    for pattern in ["/dev/serial/by-id/*", "/dev/ttyUSB*", "/dev/ttyACM*"]:
        devices.update(glob.glob(pattern))
    return devices


def query_can_devices():
    env = detect_environment()
    if not env["flash_tool"] or not env["bootloader"]:
        return {"devices": [], "error": "_backend.err_no_tool"}

    can_if = env["can_interface"] or "can0"

    try:
        if env["bootloader"] == "katapult":
            result = subprocess.run(
                [KLIPPER_ENV, env["flash_tool"], "-i", can_if, "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        else:
            result = subprocess.run(
                [KLIPPER_ENV, env["flash_tool"], "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )

        output = result.stdout + result.stderr
        uuids = re.findall(r"[0-9a-f]{16,}", output)
        return {
            "devices": list(set(uuids)),
            "raw_output": output,
            "can_interface": can_if,
        }
    except Exception as e:
        return {"devices": [], "error": str(e)}


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
        klipper_scripts = os.path.join(KLIPPER_DIR, "scripts")
        subprocess.run(enter_cmd, cwd=klipper_scripts, capture_output=True, timeout=15)
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

            if bootloader == "katapult":
                cmd = [
                    KLIPPER_ENV,
                    flash_tool,
                    "-i",
                    can_interface,
                    "-f",
                    fw_file,
                    "-u",
                    can_uuid,
                ]
            else:
                cmd = [KLIPPER_ENV, flash_tool, "-f", fw_file, "-u", can_uuid]

        elif mode == "USB":
            if not serial_device:
                task.status = "failed"
                log(_t(lang, "err_no_serial"))
                return

            log(_t(lang, "enter_bl", device=serial_device))
            bootloader_serial = detect_bootloader_serial(serial_device, try_enter=True)

            if bootloader == "katapult":
                cmd = [KLIPPER_ENV, flash_tool, "-d", bootloader_serial, "-f", fw_file]
            else:
                cmd = [KLIPPER_ENV, flash_tool, "-f", fw_file, "-d", bootloader_serial]

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

        if path == "/api/flash":
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
                cwd = os.path.join(KLIPPER_DIR, "scripts")
                if not os.path.isdir(cwd):
                    cwd = None
                subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=15)
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
    server = HTTPServer((HOST, PORT), FlashAPIHandler)
    print(f"\n  IDM Flash Web 服务已启动")
    print(f"  地址: http://localhost:{PORT}")
    print(f"  Moonraker: {MOONRAKER_URL}")
    print(f"  按 Ctrl+C 停止\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()

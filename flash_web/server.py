#!/usr/bin/env python3
"""
IDM 固件刷写 Web 服务
提供 REST API + 前端页面，可接入 Moonraker 体系
"""

import json
import os
import re
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
            ["ip", "-o", "link", "show"],
            capture_output=True, text=True, timeout=5
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
def query_can_devices():
    env = detect_environment()
    if not env["flash_tool"] or not env["bootloader"]:
        return {"devices": [], "error": "_backend.err_no_tool"}

    can_if = env["can_interface"] or "can0"

    try:
        if env["bootloader"] == "katapult":
            result = subprocess.run(
                [KLIPPER_ENV, env["flash_tool"], "-i", can_if, "-q"],
                capture_output=True, text=True, timeout=30
            )
        else:
            result = subprocess.run(
                [KLIPPER_ENV, env["flash_tool"], "-q"],
                capture_output=True, text=True, timeout=30
            )

        output = result.stdout + result.stderr
        uuids = re.findall(r"[0-9a-f]{16,}", output)
        return {"devices": list(set(uuids)), "raw_output": output, "can_interface": can_if}
    except Exception as e:
        return {"devices": [], "error": str(e)}


def query_usb_devices():
    devices = []
    for pattern in ["/dev/serial/by-id/*", "/dev/ttyUSB*", "/dev/ttyACM*"]:
        import glob
        devices.extend(glob.glob(pattern))
    return {"devices": sorted(set(devices))}


def query_dfu_devices():
    try:
        result = subprocess.run(
            ["sudo", "dfu-util", "-l"],
            capture_output=True, text=True, timeout=10
        )
        return {"raw_output": result.stdout + result.stderr, "devices_found": "Found" in result.stdout}
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
        versions.append({"label": "最新版", "files": sorted(current_files, key=lambda x: x["name"])})

    old_dir = base_dir / "old"
    if old_dir.exists() and old_dir.is_dir():
        for version_dir in sorted(old_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                ver_files = []
                for f in version_dir.rglob("*"):
                    if f.is_file() and f.suffix in (".bin", ".uf2"):
                        if is_rp2040:
                            is_dep = "deployer" in f.name.lower() or "canboot_" in f.name.lower()
                            is_main = "idm_" in f.name.lower() or "IDM_" in f.name
                            if is_deployer and not is_dep:
                                continue
                            if not is_deployer and not is_main:
                                continue
                        ver_files.append({"name": f.name, "path": str(f)})
                if ver_files:
                    versions.append({
                        "label": version_dir.name,
                        "files": sorted(ver_files, key=lambda x: x["name"]),
                    })

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
                cmd = [KLIPPER_ENV, flash_tool, "-i", can_interface, "-f", fw_file, "-u", can_uuid]
            else:
                cmd = [KLIPPER_ENV, flash_tool, "-f", fw_file, "-u", can_uuid]

        elif mode == "USB":
            if not serial_device:
                task.status = "failed"
                log(_t(lang, "err_no_serial"))
                return

            log(_t(lang, "enter_bl", device=serial_device))
            enter_cmd = [
                KLIPPER_ENV, "-c",
                f"import flash_usb as u; u.enter_bootloader('{serial_device}')"
            ]
            subprocess.run(enter_cmd, cwd=os.path.join(KLIPPER_DIR, "scripts"),
                           capture_output=True, timeout=15)
            time.sleep(3)

            bootloader_serial = params.get("bootloader_serial", serial_device)

            if bootloader == "katapult":
                cmd = [KLIPPER_ENV, flash_tool, "-d", bootloader_serial, "-f", fw_file]
            else:
                cmd = [KLIPPER_ENV, flash_tool, "-f", fw_file, "-d", bootloader_serial]

        elif mode == "DFU":
            cmd = ["sudo", "dfu-util", "-d", ",0483:df11", "-R", "-a", "0",
                   "-s", f"{dfu_addr}:leave", "-D", fw_file]

        else:
            task.status = "failed"
            log(_t(lang, "err_unknown_mode", mode=mode))
            return

        log(_t(lang, "exec_cmd", cmd=" ".join(cmd)))

        process = subprocess.Popen(
            cmd,
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

        if process.returncode == 0:
            task.status = "completed"
            log(_t(lang, "flash_done"))
        else:
            task.status = "failed"
            log(_t(lang, "flash_fail", code=str(process.returncode)))

    except subprocess.TimeoutExpired:
        task.status = "failed"
        log(_t(lang, "err_timeout"))
    except Exception as e:
        task.status = "failed"
        log(f"{_t(lang, 'err_timeout')}: {str(e)}")


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

        elif path == "/api/devices/dfu":
            self.send_json(query_dfu_devices())

        elif path == "/api/firmware/list":
            qs = parse_qs(urlparse(self.path).query)
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
            self.send_json(moonraker_request("/printer/objects/query?toolhead&heater_bed&extruder"))

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
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            task_id = data.get("task_id")

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

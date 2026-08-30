#!/usr/bin/env bash
# ============================================================
# IDM Flash Web 服务启动脚本
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "  IDM Flash Web 服务"
echo "========================================="

if [[ ! -f "${SCRIPT_DIR}/server.py" ]]; then
    echo "错误: 未找到 server.py"
    exit 1
fi

export MOONRAKER_URL="${MOONRAKER_URL:-http://localhost:7125}"
export IDM_PORT="${IDM_PORT:-8888}"

if [[ -n "${KLIPPER_ENV:-}" && -f "${KLIPPER_ENV}" ]]; then
    PYTHON_BIN="${KLIPPER_ENV}"
elif [[ -f "${HOME}/klippy-env/bin/python3" ]]; then
    PYTHON_BIN="${HOME}/klippy-env/bin/python3"
elif [[ -f "${HOME}/klippy-env/bin/python" ]]; then
    PYTHON_BIN="${HOME}/klippy-env/bin/python"
else
    PYTHON_BIN="$(command -v python3)"
fi
export KLIPPER_ENV="${PYTHON_BIN}"

if [[ -z "${IDM_FW_BASE:-}" ]]; then
    if [[ -d "${SCRIPT_DIR}/../IDM固件(Main firmware)" ]]; then
        export IDM_FW_BASE="$(cd "${SCRIPT_DIR}/.." && pwd)"
    elif [[ -d "${HOME}/idm-documents/IDM固件(Main firmware)" ]]; then
        export IDM_FW_BASE="${HOME}/idm-documents"
    else
        export IDM_FW_BASE="${SCRIPT_DIR}/.."
    fi
fi

echo ""
echo "  启动地址: http://0.0.0.0:${IDM_PORT}"
echo "  Moonraker: ${MOONRAKER_URL}"
echo "  按 Ctrl+C 停止"
echo ""

cd "${SCRIPT_DIR}"
exec "${PYTHON_BIN}" server.py

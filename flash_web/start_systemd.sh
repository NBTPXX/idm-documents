#!/usr/bin/env bash
# Systemd 启动入口 — 由 idm-flash-web.service 调用
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export HOME="${HOME:-/home/user}"
export MOONRAKER_URL="${MOONRAKER_URL:-http://localhost:7125}"

if [[ -z "${IDM_FW_BASE:-}" ]]; then
    if [[ -d "${SCRIPT_DIR}/../IDM固件(Main firmware)" ]]; then
        export IDM_FW_BASE="$(cd "${SCRIPT_DIR}/.." && pwd)"
    elif [[ -d "${HOME}/idm-documents/IDM固件(Main firmware)" ]]; then
        export IDM_FW_BASE="${HOME}/idm-documents"
    fi
fi

exec python3 "${SCRIPT_DIR}/server.py"

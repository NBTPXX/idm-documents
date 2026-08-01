#!/usr/bin/env bash
# Systemd 启动入口 — 由 idm-flash-web.service 调用
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 解析真实用户家目录：getent 可用时用原方案（getent | cut），
# 不可用（精简系统）时把 /data 当作用户目录。
user_home() {
    local user="${1:-}"
    if command -v getent &>/dev/null; then
        if [[ -z "${user}" ]]; then
            user="$(id -un 2>/dev/null)"
        fi
        getent passwd "${user}" 2>/dev/null | cut -d: -f6
        return 0
    fi
    echo "/data"
}

if [[ -z "${HOME:-}" ]] || [[ "${HOME}" == "/home/user" ]]; then
    HOME="$(user_home)"
    export HOME="${HOME:-/data}"
fi

export MOONRAKER_URL="${MOONRAKER_URL:-http://localhost:7125}"
export IDM_PORT="${IDM_PORT:-8888}"

if [[ -z "${IDM_FW_BASE:-}" ]]; then
    if [[ -d "${SCRIPT_DIR}/../IDM固件(Main firmware)" ]]; then
        export IDM_FW_BASE="$(cd "${SCRIPT_DIR}/.." && pwd)"
    elif [[ -d "${HOME}/idm-documents/IDM固件(Main firmware)" ]]; then
        export IDM_FW_BASE="${HOME}/idm-documents"
    fi
fi

exec python3 "${SCRIPT_DIR}/server.py"

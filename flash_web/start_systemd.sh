#!/usr/bin/env bash
# Systemd 启动入口 — 由 idm-flash-web.service 调用
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 解析真实用户家目录，避免 systemd 环境未注入 HOME 时误用 /home/user
user_home() {
    local user="${1}"
    if command -v getent &>/dev/null; then
        getent passwd "${user}" 2>/dev/null | cut -d: -f6
        return 0
    fi
    if command -v awk &>/dev/null; then
        awk -F: -v u="${user}" '$1==u{print $6}' /etc/passwd 2>/dev/null
        return 0
    fi
    echo "${HOME:-}"
    return 0
}

if [[ -z "${HOME:-}" ]] || [[ "${HOME}" == "/home/user" ]]; then
    HOME="$(user_home "$(id -un)")"
    export HOME="${HOME:-$SCRIPT_DIR}"
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

#!/usr/bin/env bash
# Systemd 启动入口 — 由 idm-flash-web.service 调用
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 解析真实用户家目录：用 python3（server.py 硬依赖，精简系统必有）解析，
# 不依赖 getent/awk/cut/id 等外部命令。不带参数时解析当前用户。
user_home() {
    python3 - "${1:-}" <<'PYEOF' 2>/dev/null
import os, pwd, sys
arg = sys.argv[1] if len(sys.argv) > 1 else None
if arg:
    try:
        print(pwd.getpwnam(arg).pw_dir)
    except KeyError:
        pass
else:
    try:
        print(pwd.getpwuid(os.getuid()).pw_dir)
    except KeyError:
        pass
PYEOF
}

if [[ -z "${HOME:-}" ]] || [[ "${HOME}" == "/home/user" ]]; then
    HOME="$(user_home)"
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

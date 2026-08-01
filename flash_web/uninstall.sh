#!/usr/bin/env bash
# ============================================================
# IDM Flash Web - Uninstall Script
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${CYAN}  -> $1${NC}"; }
print_ok()   { echo -e "${GREEN}  OK $1${NC}"; }

SERVICE_NAME="idm_flash_web"
SERVICE_NAME_ALT="idm-flash-web"
UPDATE_NAME="idm_flash_web"

# 用户信息解析：与 install.sh 保持一致。getent 可用时用原方案，
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

USER_HOME="${HOME:-$(user_home)}"
USER_HOME="${USER_HOME:-/data}"

# printer_data 目录：getent 存在时用家目录下 printer_data，
# 无 getent（/data 基准）时优先 /usr/share/printer_data，其次家目录下的 printer_data
printer_data_dir() {
    local d
    if command -v getent &>/dev/null; then
        echo "${USER_HOME}/printer_data"
        return 0
    fi
    for d in "/usr/share/printer_data" "${USER_HOME}/printer_data"; do
        if [[ -d "${d}" ]]; then
            echo "${d}"
            return 0
        fi
    done
    echo "/usr/share/printer_data"
}
PD_DIR="$(printer_data_dir)"

echo ""
echo "========================================="
echo "  IDM Flash Web Uninstaller"
echo "========================================="
echo ""

_stop_service() {
    local name=$1
    if systemctl --user is-active --quiet "${name}" 2>/dev/null; then
        print_info "Stopping user-level service: ${name}"
        systemctl --user stop "${name}" 2>/dev/null || true
        systemctl --user disable "${name}" 2>/dev/null || true
        rm -f "${USER_HOME}/.config/systemd/user/${name}.service"
        systemctl --user daemon-reload 2>/dev/null || true
        print_ok "User service removed"
    elif systemctl is-active --quiet "${name}" 2>/dev/null; then
        print_info "Stopping system-level service: ${name}"
        sudo systemctl stop "${name}" 2>/dev/null || true
        sudo systemctl disable "${name}" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/${name}.service"
        sudo systemctl daemon-reload 2>/dev/null || true
        print_ok "System service removed"
    else
        print_info "Service ${name} is not running, cleaning up files..."
        sudo rm -f "/etc/systemd/system/${name}.service"
        rm -f "${USER_HOME}/.config/systemd/user/${name}.service"
    fi
}

_stop_service "${SERVICE_NAME}"
_stop_service "${SERVICE_NAME_ALT}"

# Remove from moonraker.asvc
ASVC_FILE="${PD_DIR}/moonraker.asvc"
if [[ -f "${ASVC_FILE}" ]]; then
    for name in "${SERVICE_NAME}" "${SERVICE_NAME_ALT}"; do
        if grep -q "^${name}$" "${ASVC_FILE}" 2>/dev/null; then
            print_info "Removing ${name} from moonraker.asvc ..."
            grep -v "^${name}$" "${ASVC_FILE}" > "${ASVC_FILE}.tmp" && mv "${ASVC_FILE}.tmp" "${ASVC_FILE}"
            print_ok "Removed from moonraker.asvc"
        fi
    done
fi

# Remove Moonraker update_manager config
for conf in \
    "${PD_DIR}/config/moonraker.conf" \
    "${USER_HOME}/klipper_config/moonraker.conf" \
    "${USER_HOME}/moonraker.conf"; do
    if [[ -f "${conf}" ]] && grep -q "\[update_manager ${UPDATE_NAME}\]" "${conf}" 2>/dev/null; then
        print_info "Removing Moonraker [update_manager ${UPDATE_NAME}] config..."
        python3 - "${conf}" "${UPDATE_NAME}" <<'PYEOF' > "${conf}.tmp" && mv "${conf}.tmp" "${conf}"
import re, sys
path, name = sys.argv[1], sys.argv[2]
pat = re.compile(r"^\[update_manager " + re.escape(name) + r"\]\s*$")
out, skip = [], False
with open(path, encoding="utf-8") as f:
    for line in f:
        if pat.match(line):
            skip = True
            continue
        if skip and line.startswith("["):
            skip = False
        if not skip:
            out.append(line)
sys.stdout.write("".join(out))
PYEOF
        print_ok "Removed from ${conf}"
    fi
done

echo ""
print_ok "Uninstall complete"

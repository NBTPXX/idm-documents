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

SERVICE_NAME="idm-flash-web"
SERVICE_NAME_ALT="idm_flash_web"
UPDATE_NAME="idm_flash_web"

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
        rm -f "${HOME}/.config/systemd/user/${name}.service"
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
        rm -f "${HOME}/.config/systemd/user/${name}.service"
    fi
}

_stop_service "${SERVICE_NAME}"
_stop_service "${SERVICE_NAME_ALT}"

# Remove from moonraker.asvc
ASVC_FILE="${HOME}/printer_data/moonraker.asvc"
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
    "${HOME}/printer_data/config/moonraker.conf" \
    "${HOME}/klipper_config/moonraker.conf" \
    "${HOME}/moonraker.conf"; do
    if [[ -f "${conf}" ]] && grep -q "\[update_manager ${UPDATE_NAME}\]" "${conf}" 2>/dev/null; then
        print_info "Removing Moonraker [update_manager ${UPDATE_NAME}] config..."
        awk -v name="${UPDATE_NAME}" '
          BEGIN { skip=0 }
          $0 ~ "^\\[update_manager " name "\\]" { skip=1; next }
          skip && /^\[/ { skip=0 }
          !skip { print }
        ' "${conf}" > "${conf}.tmp" && mv "${conf}.tmp" "${conf}"
        print_ok "Removed from ${conf}"
    fi
done

echo ""
print_ok "Uninstall complete"

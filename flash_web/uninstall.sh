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
INSTALL_DIR="${HOME}/IDM/flash_web"
UPDATE_NAME="idm_flash_web"

echo ""
echo "========================================="
echo "  IDM Flash Web Uninstaller"
echo "========================================="
echo ""

# Stop and remove systemd service
if systemctl --user is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
    print_info "Stopping user-level service..."
    systemctl --user stop "${SERVICE_NAME}"
    systemctl --user disable "${SERVICE_NAME}"
    rm -f "${HOME}/.config/systemd/user/${SERVICE_NAME}.service"
    systemctl --user daemon-reload
    print_ok "User service removed"
elif systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
    print_info "Stopping system-level service..."
    sudo systemctl stop "${SERVICE_NAME}"
    sudo systemctl disable "${SERVICE_NAME}"
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    print_ok "System service removed"
else
    print_info "Service is not running"
fi

# Remove Moonraker update_manager config
for conf in \
    "${HOME}/printer_data/config/moonraker.conf" \
    "${HOME}/klipper_config/moonraker.conf" \
    "${HOME}/moonraker.conf"; do
    if [[ -f "${conf}" ]] && grep -q "\[update_manager ${UPDATE_NAME}\]" "${conf}" 2>/dev/null; then
        print_info "Removing Moonraker update_manager config..."
        awk -v name="${UPDATE_NAME}" '
          BEGIN { skip=0 }
          $0 ~ "^\\[update_manager " name "\\]" { skip=1; next }
          skip && /^\[/ { skip=0 }
          !skip { print }
        ' "${conf}" > "${conf}.tmp" && mv "${conf}.tmp" "${conf}"
        print_ok "Removed from ${conf}"
    fi
done

# Remove install directory
if [[ -d "${INSTALL_DIR}" ]]; then
    read -r -p "Delete install directory ${INSTALL_DIR}? [y/N]: " CONFIRM
    if [[ "${CONFIRM}" =~ ^[Yy]$ ]]; then
        rm -rf "${INSTALL_DIR}"
        print_ok "Install directory removed"
    fi
fi

echo ""
print_ok "Uninstall complete"

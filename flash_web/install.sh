#!/usr/bin/env bash
# ============================================================
# IDM Flash Web - Install Script
# Auto-configure systemd auto-start & Moonraker update_manager
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info()  { echo -e "${CYAN}  -> $1${NC}"; }
print_ok()    { echo -e "${GREEN}  OK $1${NC}"; }
print_warn()  { echo -e "${YELLOW}  !! $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_NAME="idm-flash-web"
SERVICE_PORT="8888"

PYTHON_BIN="python3"
if [[ -f "${HOME}/klippy-env/bin/python" ]]; then
    PYTHON_BIN="${HOME}/klippy-env/bin/python"
    print_info "Using Klipper Python: ${PYTHON_BIN}"
fi

echo ""
echo "========================================="
echo "  IDM Flash Web Installer"
echo "========================================="
echo ""

# -----------------------------------------------------------
# 1. Ensure scripts are executable
# -----------------------------------------------------------
print_info "Setting up ${SCRIPT_DIR} ..."
chmod +x "${SCRIPT_DIR}/start.sh"
chmod +x "${SCRIPT_DIR}/start_systemd.sh"
chmod +x "${SCRIPT_DIR}/server.py"
print_ok "Done"

# -----------------------------------------------------------
# 2. Configure Moonraker update_manager
# -----------------------------------------------------------
UPDATE_NAME="idm_flash_web"
MOONRAKER_CONF=""

for path in \
    "${HOME}/printer_data/config/moonraker.conf" \
    "${HOME}/klipper_config/moonraker.conf" \
    "${HOME}/moonraker.conf"; do
    if [[ -f "${path}" ]]; then
        MOONRAKER_CONF="${path}"
        break
    fi
done

if [[ -z "${MOONRAKER_CONF}" ]]; then
    print_warn "moonraker.conf not found, skipping update_manager config"
else
    if grep -q "\[update_manager ${UPDATE_NAME}\]" "${MOONRAKER_CONF}" 2>/dev/null; then
        print_info "[update_manager ${UPDATE_NAME}] already exists, skipping"
    else
        print_info "Adding [update_manager ${UPDATE_NAME}] to ${MOONRAKER_CONF} ..."

        REPO_REMOTE=$(cd "${REPO_DIR}" && git remote get-url origin 2>/dev/null || echo "https://gitee.com/NBTP/idm-documents.git")

        cat >> "${MOONRAKER_CONF}" <<EOF

[update_manager ${UPDATE_NAME}]
type: git_repo
channel: dev
path: ${REPO_DIR}
origin: ${REPO_REMOTE}
is_system_service: False
info_tags:
    desc=IDM Flash Web Tool
EOF

        print_ok "Moonraker update_manager configured"
    fi

    if grep -q "\[service ${SERVICE_NAME}\]" "${MOONRAKER_CONF}" 2>/dev/null; then
        print_info "[service ${SERVICE_NAME}] already exists, skipping"
    else
        print_info "Adding [service ${SERVICE_NAME}] to ${MOONRAKER_CONF} ..."
        cat >> "${MOONRAKER_CONF}" <<EOF

[service ${SERVICE_NAME}]
type: systemd
EOF
        print_ok "Moonraker service registered"
    fi

    print_info "Restart Moonraker to apply: sudo systemctl restart moonraker"
fi

# -----------------------------------------------------------
# 3. Install systemd service
# -----------------------------------------------------------
SERVICE_FILE="${SCRIPT_DIR}/idm-flash-web.service"
SYSTEMD_DIR="/etc/systemd/system"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

if [[ -f "${SERVICE_FILE}" ]]; then
    sed "s|__FLASH_WEB_DIR__|${SCRIPT_DIR}|g" "${SERVICE_FILE}" > "/tmp/${SERVICE_NAME}.service"
    echo "Environment=IDM_FW_BASE=${REPO_DIR}" >> "/tmp/${SERVICE_NAME}.service"

    if command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
        print_info "Installing system-level systemd service..."
        sudo cp "/tmp/${SERVICE_NAME}.service" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"
        sudo systemctl daemon-reload
        sudo systemctl enable "${SERVICE_NAME}"
        sudo systemctl start "${SERVICE_NAME}"
        print_ok "System service installed and started"
        echo ""
        print_info "Management commands:"
        echo "    sudo systemctl status  ${SERVICE_NAME}"
        echo "    sudo systemctl restart ${SERVICE_NAME}"
        echo "    sudo systemctl stop    ${SERVICE_NAME}"
        echo "    sudo journalctl -u ${SERVICE_NAME} -f"
    else
        print_warn "sudo unavailable, installing user-level systemd service..."
        mkdir -p "${USER_SYSTEMD_DIR}"
        cp "/tmp/${SERVICE_NAME}.service" "${USER_SYSTEMD_DIR}/${SERVICE_NAME}.service"

        if command -v loginctl &>/dev/null; then
            loginctl enable-linger "${USER}" 2>/dev/null || true
        fi

        systemctl --user daemon-reload
        systemctl --user enable "${SERVICE_NAME}"
        systemctl --user start "${SERVICE_NAME}"
        print_ok "User service installed and started"
        echo ""
        print_info "Management commands:"
        echo "    systemctl --user status  ${SERVICE_NAME}"
        echo "    systemctl --user restart ${SERVICE_NAME}"
        echo "    systemctl --user stop    ${SERVICE_NAME}"
        echo "    journalctl --user -u ${SERVICE_NAME} -f"
    fi

    rm -f "/tmp/${SERVICE_NAME}.service"
else
    print_warn "Service file not found, skipping systemd config"
    print_info "Manual start: ${SCRIPT_DIR}/start.sh"
fi

# -----------------------------------------------------------
# 4. Check service status
# -----------------------------------------------------------
echo ""
print_info "Checking port ${SERVICE_PORT} ..."
sleep 2
if ss -tlnp 2>/dev/null | grep -q ":${SERVICE_PORT} "; then
    print_ok "Service is running on port ${SERVICE_PORT}"
else
    print_warn "Port ${SERVICE_PORT} not listening, check logs"
fi

# -----------------------------------------------------------
# 5. Done
# -----------------------------------------------------------
echo ""
echo "========================================="
print_ok "Installation complete!"
echo ""
echo "  URL: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<device-IP>'):${SERVICE_PORT}"
echo "  Logs: sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "  Embed in Mainsail/Fluidd via iframe"
echo "========================================="

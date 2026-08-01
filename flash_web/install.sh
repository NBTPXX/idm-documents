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
SERVICE_NAME="idm_flash_web"
SERVICE_PORT="${IDM_PORT:-8888}"

# 用户信息解析：用 python3（server.py 的硬依赖，精简系统必有），
# 不依赖 getent/awk/cut/id 等外部命令。
user_name() {
    python3 -c 'import os, pwd; print(pwd.getpwuid(os.getuid()).pw_name)' 2>/dev/null
}

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

SERVICE_SCOPE="user"
SERVICE_USER="${USER:-$(user_name)}"
SERVICE_HOME="${HOME:-$(user_home)}"

port_in_use() {
    ss -tln 2>/dev/null | grep -q ":${1} "
}

next_free_port() {
    local port="${1}"
    while port_in_use "${port}"; do
        port=$((port + 1))
    done
    echo "${port}"
}

choose_port() {
    # 仅在用户未显式指定 IDM_PORT 时进行端口选择
    if [[ -n "${IDM_PORT:-}" ]]; then
        if port_in_use "${SERVICE_PORT}"; then
            print_warn "Port ${SERVICE_PORT} (IDM_PORT) is already in use"
        fi
        return
    fi
    if port_in_use "${SERVICE_PORT}"; then
        print_warn "Port ${SERVICE_PORT} is already in use"
        local suggested
        suggested="$(next_free_port "${SERVICE_PORT}")"
        print_info "Suggested free port: ${suggested}"
        local user_port=""
        if [[ -t 0 ]] && command -v read &>/dev/null; then
            if read -r -p "Enter a new port (default ${suggested}): " user_port; then
                if [[ -n "${user_port}" ]]; then
                    SERVICE_PORT="${user_port}"
                else
                    SERVICE_PORT="${suggested}"
                fi
            else
                SERVICE_PORT="${suggested}"
            fi
        else
            SERVICE_PORT="${suggested}"
            print_info "Non-interactive install, using port ${SERVICE_PORT}"
        fi
        if port_in_use "${SERVICE_PORT}"; then
            print_warn "Port ${SERVICE_PORT} is still in use, start may fail. Free it or re-run with IDM_PORT=<port>"
        fi
    fi
}

if command -v sudo &>/dev/null && sudo -v; then
    SERVICE_SCOPE="system"
    SERVICE_HOME="$(user_home "${SERVICE_USER}")"
    SERVICE_HOME="${SERVICE_HOME:-${HOME}}"
fi

if [[ "${SERVICE_SCOPE}" == "system" ]]; then
    IS_SYSTEM_SERVICE="True"
else
    IS_SYSTEM_SERVICE="False"
fi

PYTHON_BIN="python3"
if [[ -f "${HOME}/klippy-env/bin/python3" ]]; then
    PYTHON_BIN="${HOME}/klippy-env/bin/python3"
    print_info "Using Klipper Python: ${PYTHON_BIN}"
elif [[ -f "${HOME}/klippy-env/bin/python" ]]; then
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

# 端口选择：8888 被占用时允许用户换端口
choose_port
print_info "Using port ${SERVICE_PORT}"


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
        if grep -A10 "\[update_manager ${UPDATE_NAME}\]" "${MOONRAKER_CONF}" | grep -q "^is_system_service:"; then
            sed -i "/^\[update_manager ${UPDATE_NAME}\]/,/^\[/{s/^is_system_service:.*/is_system_service: ${IS_SYSTEM_SERVICE}/}" "${MOONRAKER_CONF}"
        else
            sed -i "/^\[update_manager ${UPDATE_NAME}\]/a is_system_service: ${IS_SYSTEM_SERVICE}" "${MOONRAKER_CONF}"
        fi
        if ! grep -A10 "\[update_manager ${UPDATE_NAME}\]" "${MOONRAKER_CONF}" \
             | grep -q "managed_services:"; then
            print_info "Adding managed_services: ${UPDATE_NAME} ..."
            sed -i "/^is_system_service:/a managed_services: ${UPDATE_NAME}" "${MOONRAKER_CONF}"
        fi
    else
        print_info "Adding [update_manager ${UPDATE_NAME}] to ${MOONRAKER_CONF} ..."

        REPO_REMOTE=$(cd "${REPO_DIR}" && git remote get-url origin 2>/dev/null || echo "https://gitee.com/NBTP/idm-documents.git")

        cat >> "${MOONRAKER_CONF}" <<EOF

[update_manager ${UPDATE_NAME}]
type: git_repo
channel: dev
path: ${REPO_DIR}
origin: ${REPO_REMOTE}
is_system_service: ${IS_SYSTEM_SERVICE}
managed_services: ${UPDATE_NAME}
info_tags:
    desc=IDM Flash Web Tool
EOF

        print_ok "Moonraker update_manager configured"
    fi

    ASVC_FILE="${HOME}/printer_data/moonraker.asvc"
    if grep -q "^${SERVICE_NAME}$" "${ASVC_FILE}" 2>/dev/null; then
        print_info "${SERVICE_NAME} already in moonraker.asvc, skipping"
    else
        print_info "Adding ${SERVICE_NAME} to ${ASVC_FILE} ..."
        echo "${SERVICE_NAME}" >> "${ASVC_FILE}"
        print_ok "moonraker.asvc updated"
    fi

    print_info "Restart Moonraker to apply: sudo systemctl restart moonraker"
fi

# -----------------------------------------------------------
# 3. Install systemd service
# -----------------------------------------------------------
SERVICE_FILE="${SCRIPT_DIR}/idm_flash_web.service"
SYSTEMD_DIR="/etc/systemd/system"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

if [[ -f "${SERVICE_FILE}" ]]; then
    sed \
        -e "s|__FLASH_WEB_DIR__|${SCRIPT_DIR}|g" \
        -e "s|__FLASH_WEB_USER__|${SERVICE_USER}|g" \
        -e "s|__FLASH_WEB_HOME__|${SERVICE_HOME}|g" \
        -e "s|__FLASH_WEB_PORT__|${SERVICE_PORT}|g" \
        "${SERVICE_FILE}" > "/tmp/${SERVICE_NAME}.service"

    if [[ "${SERVICE_SCOPE}" == "system" ]]; then
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

        if command -v loginctl &>/dev/null && loginctl enable-linger "${USER}"; then
            print_ok "User service will start after reboot"
        else
            print_warn "Unable to enable user linger; run: sudo loginctl enable-linger ${USER}"
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
echo "  URL: http://$(python3 -c 'import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80)); print(s.getsockname()[0]); s.close()' 2>/dev/null || echo '<device-IP>'):${SERVICE_PORT}"
echo "  Logs: sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "  Embed in Mainsail/Fluidd via iframe"
echo "========================================="

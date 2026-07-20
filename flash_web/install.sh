#!/usr/bin/env bash
# ============================================================
# IDM Flash Web - 安装脚本
# 安装后自动配置 systemd 开机自启
# 仿照 Fluidd / Mainsail 安装方式
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
INSTALL_DIR="${HOME}/IDM/flash_web"
SERVICE_NAME="idm-flash-web"
SERVICE_PORT="8888"

# 检测 Python
PYTHON_BIN="python3"
if [[ -f "${HOME}/klippy-env/bin/python" ]]; then
    PYTHON_BIN="${HOME}/klippy-env/bin/python"
    print_info "使用 Klipper 环境 Python: ${PYTHON_BIN}"
fi

echo ""
echo "========================================="
echo "  IDM Flash Web 安装脚本"
echo "========================================="
echo ""

# -----------------------------------------------------------
# 1. 安装文件
# -----------------------------------------------------------
print_info "安装文件到 ${INSTALL_DIR} ..."
mkdir -p "${INSTALL_DIR}/templates"
mkdir -p "${INSTALL_DIR}/i18n"

cp "${SCRIPT_DIR}/server.py"       "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/start.sh"        "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/start_systemd.sh" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/templates/index.html" "${INSTALL_DIR}/templates/"
cp "${SCRIPT_DIR}/i18n/"*.json           "${INSTALL_DIR}/i18n/"

chmod +x "${INSTALL_DIR}/start.sh"
chmod +x "${INSTALL_DIR}/start_systemd.sh"
chmod +x "${INSTALL_DIR}/server.py"

print_ok "文件已安装"

# -----------------------------------------------------------
# 2. 配置 Moonraker update_manager
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
    print_warn "未找到 moonraker.conf，跳过 update_manager 配置"
else
    if grep -q "\[update_manager ${UPDATE_NAME}\]" "${MOONRAKER_CONF}" 2>/dev/null; then
        print_info "[update_manager ${UPDATE_NAME}] 已存在，跳过"
    else
        print_info "添加 [update_manager ${UPDATE_NAME}] 到 ${MOONRAKER_CONF} ..."

        REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
        REPO_REMOTE=$(cd "${REPO_DIR}" && git remote get-url origin 2>/dev/null || echo "https://gitee.com/NBTP/idm-documents.git")

        cat >> "${MOONRAKER_CONF}" <<EOF

[update_manager ${UPDATE_NAME}]
type: git_repo
channel: dev
path: ${REPO_DIR}
origin: ${REPO_REMOTE}
env: ${PYTHON_BIN}
requirements: requirements.txt
install_script: flash_web/install.sh
is_system_service: False
managed_services: klipper
info_tags:
    desc=IDM Flash Web Tool
EOF

        print_ok "Moonraker update_manager 已配置"
        print_info "重启 Moonraker 后生效: sudo systemctl restart moonraker"
    fi
fi

# -----------------------------------------------------------
# 3. 安装 systemd 服务
# -----------------------------------------------------------
SERVICE_FILE="${SCRIPT_DIR}/idm-flash-web.service"
SYSTEMD_DIR="/etc/systemd/system"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

if [[ -f "${SERVICE_FILE}" ]]; then
    # 先将 %h 替换为实际 HOME 路径
    sed "s|%h|${HOME}|g" "${SERVICE_FILE}" > "/tmp/${SERVICE_NAME}.service"

    if command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
        # 系统级安装 (需要 sudo)
        print_info "安装系统级 systemd 服务..."
        sudo cp "/tmp/${SERVICE_NAME}.service" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"
        sudo systemctl daemon-reload
        sudo systemctl enable "${SERVICE_NAME}"
        sudo systemctl start "${SERVICE_NAME}"
        print_ok "系统服务已安装并启动"
        echo ""
        print_info "管理命令:"
        echo "    sudo systemctl status  ${SERVICE_NAME}"
        echo "    sudo systemctl restart ${SERVICE_NAME}"
        echo "    sudo systemctl stop    ${SERVICE_NAME}"
        echo "    sudo journalctl -u ${SERVICE_NAME} -f"
    else
        # 用户级安装 (不需要 sudo)
        print_warn "无法使用 sudo, 安装用户级 systemd 服务..."
        mkdir -p "${USER_SYSTEMD_DIR}"
        cp "/tmp/${SERVICE_NAME}.service" "${USER_SYSTEMD_DIR}/${SERVICE_NAME}.service"

        # 启用 linger 防止用户退出后服务停止
        if command -v loginctl &>/dev/null; then
            loginctl enable-linger "${USER}" 2>/dev/null || true
        fi

        systemctl --user daemon-reload
        systemctl --user enable "${SERVICE_NAME}"
        systemctl --user start "${SERVICE_NAME}"
        print_ok "用户服务已安装并启动"
        echo ""
        print_info "管理命令:"
        echo "    systemctl --user status  ${SERVICE_NAME}"
        echo "    systemctl --user restart ${SERVICE_NAME}"
        echo "    systemctl --user stop    ${SERVICE_NAME}"
        echo "    journalctl --user -u ${SERVICE_NAME} -f"
    fi

    rm -f "/tmp/${SERVICE_NAME}.service"
else
    print_warn "未找到 service 文件, 跳过 systemd 配置"
    print_info "手动启动: ${INSTALL_DIR}/start.sh"
fi

# -----------------------------------------------------------
# 4. 检查服务状态
# -----------------------------------------------------------
echo ""
print_info "检查服务端口 ${SERVICE_PORT} ..."
sleep 2
if ss -tlnp 2>/dev/null | grep -q ":${SERVICE_PORT} "; then
    print_ok "服务已在端口 ${SERVICE_PORT} 运行"
else
    print_warn "端口 ${SERVICE_PORT} 未检测到监听, 请检查日志"
fi

# -----------------------------------------------------------
# 4. 完成
# -----------------------------------------------------------
echo ""
echo "========================================="
print_ok "安装完成!"
echo ""
echo "  访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<设备IP>'):${SERVICE_PORT}"
echo "  日志查看: sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "  在 Mainsail / Fluidd 中可通过 iframe 嵌入此地址"
echo "========================================="

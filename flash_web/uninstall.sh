#!/usr/bin/env bash
# ============================================================
# IDM Flash Web - 卸载脚本
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${CYAN}  -> $1${NC}"; }
print_ok()   { echo -e "${GREEN}  OK $1${NC}"; }

SERVICE_NAME="idm-flash-web"
INSTALL_DIR="${HOME}/IDM/flash_web"

echo ""
echo "========================================="
echo "  IDM Flash Web 卸载脚本"
echo "========================================="
echo ""

# 停止并移除 systemd 服务
if systemctl --user is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
    print_info "停止用户级服务..."
    systemctl --user stop "${SERVICE_NAME}"
    systemctl --user disable "${SERVICE_NAME}"
    rm -f "${HOME}/.config/systemd/user/${SERVICE_NAME}.service"
    systemctl --user daemon-reload
    print_ok "用户服务已移除"
elif systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
    print_info "停止系统级服务..."
    sudo systemctl stop "${SERVICE_NAME}"
    sudo systemctl disable "${SERVICE_NAME}"
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    print_ok "系统服务已移除"
else
    print_info "服务未在运行"
fi

# 移除安装目录
if [[ -d "${INSTALL_DIR}" ]]; then
    read -r -p "是否删除安装目录 ${INSTALL_DIR} ? [y/N]: " CONFIRM
    if [[ "${CONFIRM}" =~ ^[Yy]$ ]]; then
        rm -rf "${INSTALL_DIR}"
        print_ok "安装目录已删除"
    fi
fi

echo ""
print_ok "卸载完成"

#!/usr/bin/env bash
# ============================================================
# IDM Flash Web 服务启动脚本
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "  IDM Flash Web 服务"
echo "========================================="

if [[ ! -f "${SCRIPT_DIR}/server.py" ]]; then
    echo "错误: 未找到 server.py"
    exit 1
fi

export MOONRAKER_URL="${MOONRAKER_URL:-http://localhost:7125}"

echo ""
echo "  启动地址: http://0.0.0.0:8888"
echo "  Moonraker: ${MOONRAKER_URL}"
echo "  按 Ctrl+C 停止"
echo ""

cd "${SCRIPT_DIR}"
python3 server.py

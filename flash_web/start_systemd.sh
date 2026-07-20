#!/usr/bin/env bash
# Systemd 启动入口 — 由 idm-flash-web.service 调用
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export MOONRAKER_URL="${MOONRAKER_URL:-http://localhost:7125}"

exec python3 "${SCRIPT_DIR}/server.py"

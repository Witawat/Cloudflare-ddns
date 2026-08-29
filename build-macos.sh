#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
  echo "ไม่พบ PyInstaller — สร้าง venv แล้วติดตั้งก่อน:"
  echo "  python3 -m venv .build-venv"
  echo "  .build-venv/bin/python -m pip install pyinstaller"
  echo "  PYTHON_BIN=\"$PWD/.build-venv/bin/python\" ./build-macos.sh"
  exit 1
fi

echo "[1/2] Building macOS executable..."
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean --onefile --console \
  --name cloudflare-ddns \
  --add-data "cloudflare_ddns/webui.html:cloudflare_ddns" \
  --add-data "cloudflare_ddns/webui.js:cloudflare_ddns" \
  --add-data "cloudflare_ddns/webui_login.html:cloudflare_ddns" \
  run.py

echo "[2/2] Done: dist/cloudflare-ddns"
echo "ทดสอบ: ./dist/cloudflare-ddns status"

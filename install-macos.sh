#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -x "dist/cloudflare-ddns" ]]; then
  DDNS_CMD=("$PWD/dist/cloudflare-ddns")
else
  DDNS_CMD=(python3 -m cloudflare_ddns.main)
fi

echo "[1/2] ติดตั้ง macOS LaunchAgent..."
"${DDNS_CMD[@]}" install
echo "[2/2] เริ่ม LaunchAgent..."
"${DDNS_CMD[@]}" start
echo "เรียบร้อย — เปิด Web UI: http://127.0.0.1:8123"
echo "ตรวจสถานะ: ${DDNS_CMD[*]} status"

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -x "dist/cloudflare-ddns" ]]; then
  DDNS_CMD=("$PWD/dist/cloudflare-ddns")
else
  DDNS_CMD=(python3 -m cloudflare_ddns.main)
fi

"${DDNS_CMD[@]}" remove
echo "ลบ LaunchAgent แล้ว — config/state/log ยังอยู่ในโฟลเดอร์โปรแกรม"

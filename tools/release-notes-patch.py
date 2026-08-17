"""อัปเดต release notes บน GitHub ผ่าน API ตรง (PATCH) — ข้าม bug ของ gh CLI บน Windows
ที่อ่านไฟล์ --notes-file เป็น cp874 -> ภาษาไทยเพี้ยน (mojibake) บน GitHub

วิธีใช้:
    python tools/release-notes-patch.py <tag> <notes.md> [--repo owner/repo]

ทำ 4 อย่าง:
1. หา release id จาก tag
2. ดึง SHA256 digest ของ asset แรก (exe) แล้วแทนที่ placeholder ใน notes
   (รองรับทั้ง "<SHA256...>" และ "sha256:<64hex>" ที่เป็นค่าเดิม)
3. PATCH body ผ่าน GitHub API (JSON utf-8) — ไม่ผ่าน gh CLI
4. เขียน body ที่ GitHub เก็บจริงลง <notes.md>.checked — ตรวจด้วย editor/read tool
   (ห้ามตรวจผ่าน PowerShell pipeline — PS 5.1 รับ stdout ของ native app เป็น cp874)

ต้องมี token: ใช้ `gh auth token` (ติดตั้ง gh + login แล้ว) หรือตัวแปร GH_TOKEN
"""

import json
import os
import re
import subprocess
import sys
import urllib.request

DEFAULT_REPO = "Witawat/Cloudflare-ddns"


def get_token():
    env = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if env:
        return env.strip()
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def api(token, url, method="GET", payload=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    tag = sys.argv[1]
    notes_path = sys.argv[2]
    repo = DEFAULT_REPO
    for i, arg in enumerate(sys.argv):
        if arg == "--repo" and i + 1 < len(sys.argv):
            repo = sys.argv[i + 1]

    token = get_token()
    base = f"https://api.github.com/repos/{repo}/releases"

    release = api(token, f"{base}/tags/{tag}")
    release_id = release["id"]
    print(f"release id: {release_id} ({tag})")

    assets = api(token, f"{base}/{release_id}/assets")
    digest = ""
    if assets:
        digest = str(assets[0].get("digest", "")).strip()
    print(f"asset digest: {digest or '(ไม่มี asset)'}")
    digest_hex = digest.split(":")[-1] if digest else ""  # "sha256:xxxx" -> "xxxx"

    with open(notes_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    # แทนที่ placeholder / SHA เดิมด้วย digest จริง (64 hex ไม่มี prefix)
    if digest_hex:
        replaced = False
        new_body = re.sub(
            r"SHA256:\s*`?<[^>]+>`?",
            f"SHA256: `{digest_hex}`",
            body,
            count=1,
        )
        if new_body != body:
            body = new_body
            replaced = True
        if not replaced:
            new_body = re.sub(
                r"SHA256:\s*`?[0-9A-Fa-f]{64}`?",
                f"SHA256: `{digest_hex}`",
                body,
                count=1,
            )
            if new_body != body:
                body = new_body
                replaced = True
        if not replaced:
            print("หมายเหตุ: ไม่พบบรรทัด SHA256 ใน notes — ไม่เติมให้")

    updated = api(token, f"{base}/{release_id}", method="PATCH", payload={"body": body})
    print(f"PATCH ok — body length: {len(updated['body'])}")

    checked = notes_path + ".checked"
    with open(checked, "w", encoding="utf-8") as handle:
        handle.write(updated["body"])
    print(f"บันทึก body ที่ GitHub เก็บจริง: {checked}")
    print("ตรวจภาษาไทยด้วย editor/read tool — ห้ามผ่าน PowerShell pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(main())

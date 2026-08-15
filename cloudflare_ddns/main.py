"""Entry point หลัก: setup / run / dry-run / install / start / stop / restart / remove / status / webui.

ตัวอย่าง:
    python -m cloudflare_ddns.main setup      # ตั้งค่าครั้งแรก (ถามทีละขั้น)
    python -m cloudflare_ddns.main run        # รันแบบ foreground (ทดสอบ)
    python -m cloudflare_ddns.main dry-run    # เทสต์รอบเดียว ไม่แตะ record จริง
    python -m cloudflare_ddns.main install    # ติดตั้งเป็น Windows Service (ต้อง admin)
    python -m cloudflare_ddns.main start      # เริ่ม service
    python -m cloudflare_ddns.main status     # ดูสถานะ service + IP ล่าสุด
    python -m cloudflare_ddns.main webui      # เปิด Web UI ที่ http://127.0.0.1:8123
"""

import argparse
import configparser
import getpass
import logging
import os
import sys
import webbrowser

from . import cloudflare_api
from . import config as config_mod
from . import ddns
from . import notifier

log = logging.getLogger("cloudflare-ddns")


def setup_console_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)


def _ask(question, default=None):
    suffix = f" [{default}]" if default is not None else ""
    answer = input(f"{question}{suffix}: ").strip()
    if not answer and default is not None:
        return default
    return answer


def _ask_yes(question, default=True):
    hint = "Y/n" if default else "y/N"
    answer = input(f"{question} ({hint}): ").strip().lower()
    if not answer:
        return default
    return answer.startswith("y")


# ---- setup wizard ----


def cmd_setup(args):
    cfg = config_mod.Config(args.config)
    if os.path.isfile(args.config) and cfg.api_token:
        print(f"พบ config เดิมที่ {args.config}")
        if not _ask_yes("ต้องการตั้งค่าใหม่ทับหรือไม่?", default=False):
            print("ยกเลิก")
            return

    print("=" * 56)
    print("Cloudflare DDNS — ตั้งค่าครั้งแรก")
    print("สร้าง API token ที่ https://dash.cloudflare.com/profile/api-tokens")
    print("สิทธิ์ที่ต้องให้: Zone > DNS > Edit (อย่างน้อย 1 zone)")
    print("=" * 56)
    print("กำลังเปิดเบราว์เซอร์ไปหน้าสร้าง token ให้แล้ว (ถ้าไม่เปิด ใช้ลิงก์ด้านบน)...")
    webbrowser.open("https://dash.cloudflare.com/profile/api-tokens")

    token = getpass.getpass("วาง API Token: ").strip()
    if not token:
        print("ต้องใส่ token")
        sys.exit(1)

    api = cloudflare_api.CloudflareAPI(token)
    print("กำลังตรวจ token...")
    try:
        api.verify_token()
        print("✓ token ใช้งานได้")
    except cloudflare_api.CloudflareError as exc:
        print(f"✗ token ไม่ผ่านการตรวจ: {exc}")
        sys.exit(1)

    print("กำลังโหลดรายชื่อ zone...")
    try:
        zones = api.list_zones()
    except cloudflare_api.CloudflareError as exc:
        print(f"✗ เรียก zone ไม่ได้ (token อาจไม่มีสิทธิ์ Zone:Read): {exc}")
        zones = []
    print("เลือก zone (พิมพ์เลข) หรือกด Enter เพื่อพิมพ์ชื่อเอง:")
    for i, zone in enumerate(zones, 1):
        status = " (paused)" if zone.get("status") == "pending" else ""
        print(f"  {i}. {zone.get('name')}{status}")
    zone = ""
    choice = input(f"ตัวเลือก (1-{len(zones)} หรือ Enter เพื่อพิมพ์เอง): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(zones):
        zone = zones[int(choice) - 1]["name"]
    else:
        zone = _ask("ชื่อ zone (เช่น example.com)")

    records = []
    print("เพิ่ม record ทีละตัว (กด Enter ว่างเพื่อจบ)")
    while True:
        name = _ask(f"ชื่อ record {len(records) + 1} (เช่น home.example.com หรือ @ สำหรับ root)", default="")
        if not name:
            break
        if name == "@":
            name = zone
        proxied = _ask_yes("เปิด proxied (orange cloud)?", default=False)
        ttl = _ask("TTL (วินาที, 120 = อัตโนมัติ? ใช้ 120 หรือ 300)", default="120")
        try:
            ttl = max(int(ttl), 60)
        except ValueError:
            ttl = 120
        records.append({"name": name, "proxied": proxied, "ttl": ttl})
        print(f"  ✓ เพิ่ม {name} แล้ว")

    if not records:
        print("ต้องมีอย่างน้อย 1 record")
        sys.exit(1)

    # --- ตั้งค่าแจ้งเตือน Telegram (เลือกได้) ---
    telegram_settings = {}
    if _ask_yes("ตั้งค่าแจ้งเตือน Telegram หรือไม่?", default=False):
        print("สร้าง bot ผ่าน @BotFather ใน Telegram (คำสั่ง /newbot) แล้วคัดลอก token มา")
        bot_token = getpass.getpass("Bot token: ").strip()
        if bot_token:
            print("กำลังหาบทสนทนาที่คุยกับ bot (เปิดแชทกับ bot แล้วกด /start ถ้ายังไม่เคย)...")
            chat_id, error = notifier.get_chat_id(bot_token)
            if not chat_id:
                print(f"✗ {error}")
                if _ask_yes("เปิดแชทกับ bot แล้วกด /start เมื่อพร้อม ลองหาใหม่เลยไหม?", default=True):
                    chat_id, error = notifier.get_chat_id(bot_token)
            if chat_id:
                print(f"✓ พบ chat_id: {chat_id}")
                tester = notifier.TelegramNotifier(bot_token, chat_id)
                ok, err_msg = tester.send_raw("✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS")
                if ok:
                    print("✓ ส่งข้อความทดสอบสำเร็จ — ตรวจใน Telegram ได้เลย")
                else:
                    print(f"✗ ส่งข้อความทดสอบไม่ได้: {err_msg}")
                telegram_settings = {
                    "telegram_bot_token": bot_token,
                    "telegram_chat_id": chat_id,
                    "notify_start": "true",
                    "notify_stop": "true",
                    "notify_ip_change": "true",
                    "notify_error": "true",
                    "notify_created": "true",
                }
            else:
                print("ข้ามการตั้งค่า Telegram (แก้ config.ini ทีหลังได้ หรือรัน 'notify-test')")

    parser = configparser.ConfigParser(interpolation=None)
    base = {
        "api_token": token,
        "interval_seconds": "60",
        "use_ipv4": "true",
        "use_ipv6": "true",
        "webui_port": "8123",
        "webui_password": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "notify_start": "true",
        "notify_stop": "true",
        "notify_ip_change": "true",
        "notify_error": "true",
        "notify_created": "true",
    }
    base.update(telegram_settings)
    parser["cloudflare"] = base
    for rec in records:
        parser[f"record:{rec['name']}"] = {
            "zone": zone,
            "proxied": "true" if rec["proxied"] else "false",
            "ttl": str(rec["ttl"]),
            "ipv4": "true",
            "ipv6": "true",
        }

    os.makedirs(os.path.dirname(os.path.abspath(args.config)) or ".", exist_ok=True)
    with open(args.config, "w", encoding="utf-8") as handle:
        parser.write(handle)

    print()
    print(f"✓ เขียน config แล้ว: {args.config}")
    print("ขั้นตอนถัดไป:")
    print("  1. ทดสอบ:  python -m cloudflare_ddns.main dry-run")
    print("  2. ติดตั้ง service (เปิด PowerShell/cmd เป็น admin):")
    print("     python -m cloudflare_ddns.main install")
    print("     python -m cloudflare_ddns.main start")
    print("  3. หรือดู/แก้ผ่านเว็บ: python -m cloudflare_ddns.main webui")


# ---- run / dry-run ----


def cmd_run(args):
    from . import service as service_mod

    cfg = config_mod.Config(args.config)
    setup_console_logging()
    service_mod.setup_file_logging(cfg.log_dir)
    ddns.run_forever(args.config, dry_run=False)


def cmd_dry_run(args):
    setup_console_logging()
    engine = ddns.DDNSEngine(args.config, dry_run=True)
    print("Dry-run: ตรวจเท่านั้น ไม่แก้ record จริง")
    results = engine.run_once()
    changed = [r for r in results if r["action"] in ("updated", "created", "dry-run")]
    for r in results:
        if r["action"] == "error":
            print(f"  ✗ {r['record']}: {r['message']}")
    if not changed:
        print("  ไม่มีอะไรต้องอัปเดต (IP ตรงกับ record แล้ว)")
    else:
        for r in changed:
            print(f"  → {r['record']} (IPv{r['family']}): {r['message']}")
    print("เสร็จสิ้น")


def cmd_notify_test(args):
    """ส่งข้อความทดสอบผ่าน Telegram (ยืนยันว่า config ถูก)."""
    cfg = config_mod.Config(args.config)
    notify = notifier.TelegramNotifier.from_config(cfg)
    if not notify.enabled:
        print("ยังไม่ได้ตั้งค่า Telegram ใน config")
        print("  ต้องมี telegram_bot_token และ telegram_chat_id ใน [cloudflare]")
        print("  รัน 'setup' ใหม่แล้วตอบ y ตรงคำถาม Telegram หรือแก้ config.ini เอง")
        return 1
    print(f"ส่งข้อความทดสอบไปยัง chat_id={notify.chat_id}...")
    ok, error = notify.send_raw("✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS")
    if ok:
        print("✓ ส่งข้อความทดสอบสำเร็จ — ตรวจใน Telegram ได้เลย")
        return 0
    print(f"✗ ส่งไม่สำเร็จ: {error}")
    items = notifier.load_queue()
    items.append("✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS (รอส่งใหม่)")
    notifier.save_queue(items)
    print("  ข้อความถูกเก็บในคิวและจะส่งใหม่ในรอบถัดไปโดยอัตโนมัติ")
    return 1


# ---- service control ----


def cmd_install(args):
    from . import service as service_mod

    print(service_mod.install_service())


def cmd_remove(args):
    from . import service as service_mod

    print(service_mod.remove_service())


def cmd_start(args):
    from . import service as service_mod

    print(service_mod.start_service())


def cmd_stop(args):
    from . import service as service_mod

    print(service_mod.stop_service())


def cmd_restart(args):
    from . import service as service_mod

    print(service_mod.restart_service())


def cmd_status(args):
    from . import service as service_mod

    service_status = service_mod.service_status()
    print("=== Windows Service ===")
    if service_status.get("installed"):
        state_names = {"running": "กำลังทำงาน", "stopped": "หยุดอยู่", "starting": "กำลังเริ่ม"}
        print(f"  ติดตั้งแล้ว — สถานะ: {state_names.get(service_status.get('state'), service_status.get('state'))}")
    else:
        print(f"  ยังไม่ติดตั้ง ({service_status.get('message', '')})")

    print("=== DDNS ===")
    engine = ddns.DDNSEngine(args.config)
    status = engine.status()
    records = status.get("records", {})
    if records:
        for key, ip in records.items():
            print(f"  {key}: {ip}")
    else:
        print("  ยังไม่มีข้อมูล IP (รอรอบแรก)")
    print(f"  รอบล่าสุด: {status.get('last_run', '-')}")


def cmd_webui(args):
    from . import webui

    setup_console_logging()
    log.info("เปิด Web UI ที่ http://127.0.0.1:%s (ปิดด้วย Ctrl+C)", args.port or "(จาก config)")
    webui.WebUI(args.config, port=args.port, password=args.password).serve_forever()


def cmd_default(args):
    """รันโดยไม่ใส่คำสั่ง: เปิด Web UI + เบราว์เซอร์ให้เลย (ถ้า config ไม่ครบ wizard จะขึ้นเอง)."""
    from . import webui

    setup_console_logging()
    cfg = config_mod.Config(args.config)
    errors = cfg.validate()
    if errors:
        print("ยังไม่ได้ตั้งค่า — กำลังเปิดหน้าตั้งค่า (wizard)...")
    else:
        print("เปิด Web UI ที่ http://127.0.0.1:%d (ปิดด้วย Ctrl+C)" % cfg.webui_port)
    try:
        webbrowser.open(f"http://127.0.0.1:{cfg.webui_port}")
    except Exception:
        pass
    webui.WebUI(args.config).serve_forever()


def run_service_entry():
    from . import service as service_mod

    service_mod.run_service_entry()


def main(argv=None):
    # บังคับ UTF-8 เพื่อให้ print ภาษาไทย/สัญลักษณ์ได้ในทุก console ของ Windows
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--config", default=config_mod.DEFAULT_CONFIG_PATH, help="ที่อยู่ config.ini")
    parser = argparse.ArgumentParser(
        prog="python -m cloudflare_ddns.main",
        description="Cloudflare DDNS Updater — Windows service สำหรับอัปเดต DNS อัตโนมัติ",
        parents=[parent],
    )
    sub = parser.add_subparsers(dest="command")

    for name in ("setup", "run", "dry-run", "install", "remove", "start", "stop", "restart", "status", "notify-test"):
        sub.add_parser(name, parents=[parent])
    web_parser = sub.add_parser("webui", parents=[parent])
    web_parser.add_argument("--port", type=int, default=None)
    web_parser.add_argument("--password", default=None)

    args = parser.parse_args(argv)
    commands = {
        "setup": cmd_setup,
        "run": cmd_run,
        "dry-run": cmd_dry_run,
        "install": cmd_install,
        "remove": cmd_remove,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
        "notify-test": cmd_notify_test,
        "webui": cmd_webui,
    }
    if args.command is None:
        cmd_default(args)
    else:
        commands[args.command](args)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run-service":
        run_service_entry()
    else:
        main()

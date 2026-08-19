"""Entry point หลัก: setup / run / dry-run / install / start / stop / restart / remove / status / webui / notify-test.

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
import threading
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


def print_banner():
    """แสดงชื่อโปรแกรม + เวอร์ชัน + เครดิตผู้เขียน (ตอนเปิด console)"""
    from . import __version__

    print()
    print("Cloudflare DDNS Updater  v{}".format(__version__))
    print("ผู้พัฒนา: MAKER WITAWAT  ·  github.com/Witawat/Cloudflare-ddns")
    print()


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
        ttl = _ask("TTL (วินาที 60-7200 หรือ 1 = auto)", default="120")
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
        "heartbeat_min_interval": "60",
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
    # เขียนแบบ atomic (temp + replace) — กันไฟล์เสียกลางคัน/มี service อ่านอยู่
    tmp_path = args.config + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            parser.write(handle)
        os.replace(tmp_path, args.config)
    except OSError as exc:
        print(f"✗ เขียน config ไม่ได้: {exc}")
        return

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
    from . import instance_lock
    from . import service as service_mod

    cfg = config_mod.Config(args.config)
    if not instance_lock.acquire_instance_lock(args.config):
        print("✗ มีโปรแกรม/service รันอยู่แล้ว (instance เดียวเท่านั้น) — ปิดตัวเดิมก่อน แล้วลองใหม่")
        return 1
    setup_console_logging()
    print_banner()
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
    # เก็บคิวผ่าน _enqueue (กัน race กับ service ที่อ่าน-เขียนคิวพร้อมกัน)
    notify._enqueue("✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS (รอส่งใหม่)")
    print("  ข้อความถูกเก็บในคิวและจะส่งใหม่ในรอบถัดไปโดยอัตโนมัติ")
    return 1


def cmd_reset_password(args):
    """ตั้งรหัสผ่านหน้าเว็บใหม่ (ใช้เมื่อลืมรหัส) — เขียนเป็น hash ลง config แบบ atomic."""
    import configparser
    import io

    cfg = config_mod.Config(args.config)
    pw1 = getpass.getpass("รหัสผ่านหน้าเว็บใหม่ (เว้นว่าง = ลบรหัส ไม่ต้อง login): ").strip()
    if pw1:
        pw2 = getpass.getpass("พิมพ์รหัสผ่านใหม่อีกครั้ง: ").strip()
        if pw1 != pw2:
            print("✗ รหัสไม่ตรงกัน — ยกเลิก (ไม่มีการเปลี่ยนแปลง)")
            return 1
    text = cfg.raw_text()
    if not text:
        print(f"✗ อ่าน config ไม่ได้: {args.config}")
        return 1
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        print(f"✗ config ผิดรูปแบบ: {exc}")
        return 1
    if not parser.has_section("cloudflare"):
        parser.add_section("cloudflare")
    new_value = config_mod.password_hash(pw1, cfg.path) if pw1 else ""
    parser.set("cloudflare", "webui_password", new_value)
    buf = io.StringIO()
    parser.write(buf)
    # เขียนตรงแบบ atomic (ไม่ใช้ save_text — ต้องใช้ได้แม้ config ยังตั้งไม่ครบ)
    if not config_mod.atomic_write_text(cfg.path, buf.getvalue()):
        print(f"✗ เขียนไฟล์ไม่ได้: {cfg.path}")
        return 1
    cfg.reload()
    if pw1:
        print("✓ ตั้งรหัสผ่านหน้าเว็บใหม่แล้ว (เก็บเป็น hash) — session เก่าหมดอายุ ต้อง login ใหม่")
    else:
        print("✓ ลบรหัสผ่านหน้าเว็บแล้ว — เข้าเว็บได้โดยไม่ต้อง login")
    return 0


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
        state_names = {
            "running": "กำลังทำงาน",
            "stopped": "หยุดอยู่",
            "starting": "กำลังเริ่ม",
            "stopping": "กำลังหยุด",
            "resuming": "กำลังเริ่มต่อ",
            "pausing": "กำลังพัก",
            "paused": "พักอยู่",
        }
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

    try:
        from . import tunnel as tunnel_mod

        tunnel_status = tunnel_mod.TunnelManager().status(config_mod.Config(args.config))
        print("=== Cloudflare Tunnel ===")
        print(f"  เปิดใช้งาน: {'ใช่' if tunnel_status['enabled'] else 'ไม่'} | "
              f"cloudflared: {'ติดตั้งแล้ว' if tunnel_status['installed'] else 'ยังไม่ติดตั้ง'} | "
              f"รันอยู่: {'ใช่' if tunnel_status['running'] else 'ไม่'}"
              + (f" (pid {tunnel_status['pid']})" if tunnel_status["pid"] else ""))
        if tunnel_status.get("last_error"):
            print(f"  error ล่าสุด: {tunnel_status['last_error']}")
        if tunnel_status.get("log_exists"):
            print("  log: ดูได้จากเว็บ (ปุ่ม 'ดู log tunnel') หรือไฟล์ tunnel.log ข้าง exe")
    except Exception as exc:
        log.warning("อ่านสถานะ Cloudflare Tunnel ไม่ได้: %s", exc)
        print(f"  (อ่านสถานะ tunnel ไม่ได้: {exc})")


def _start_tunnel_async(tunnel_mgr, cfg):
    """เริ่ม Cloudflare Tunnel ใน thread แยก (ดาวน์โหลด cloudflared ครั้งแรกอาจนาน)."""
    try:
        ok, message = tunnel_mgr.start(cfg)
        log.info("Cloudflare Tunnel: %s", message)
    except Exception as exc:
        log.warning("เริ่ม Cloudflare Tunnel ไม่ได้: %s", exc)


def cmd_webui(args):
    from . import webui

    setup_console_logging()
    print_banner()
    try:
        ui = webui.WebUI(args.config, port=args.port, password=args.password)
    except RuntimeError as exc:
        print(f"✗ {exc}")
        return 1
    host = "127.0.0.1" if ui.host in ("0.0.0.0", "::") else ui.host
    log.info("เปิด Web UI ที่ http://%s:%s (ปิดด้วย Ctrl+C)", host, args.port or "(จาก config)")
    ui.serve_forever()


def cmd_default(args):
    """รันโดยไม่ใส่คำสั่ง: Web UI + DDNS loop + Cloudflare Tunnel พร้อมกัน (เทียบเท่า service).
    กด exe ครั้งเดียวทำงานเต็มรูปแบบ — ปิดด้วย Ctrl+C (หยุดทุกอย่าง + แจ้ง Telegram 'หยุดทำงาน')"""
    from . import instance_lock
    from . import service as service_mod
    from . import webui

    setup_console_logging()
    print_banner()
    cfg = config_mod.Config(args.config)
    if not instance_lock.acquire_instance_lock(args.config):
        print("✗ มีโปรแกรม/service รันอยู่แล้ว (instance เดียวเท่านั้น) — ปิดตัวเดิมก่อน แล้วลองใหม่")
        return 1
    errors = cfg.validate()
    if errors:
        print("ยังไม่ได้ตั้งค่า — กำลังเปิดหน้าตั้งค่า (wizard)...")
    else:
        print("เปิด Web UI + DDNS loop + Tunnel (ปิดด้วย Ctrl+C)")
    service_mod.setup_file_logging(cfg.log_dir)

    web_ui = None
    try:
        web_ui = webui.WebUI(args.config)
        web_ui.start()
        print("Web UI เปิดที่ http://127.0.0.1:%d" % web_ui.port)
    except RuntimeError as exc:
        print(f"✗ {exc}")
    except Exception as exc:
        log.warning("เปิด Web UI ไม่ได้: %s", exc)
    try:
        webbrowser.open(f"http://127.0.0.1:{cfg.webui_port}")
    except Exception:
        pass

    # เริ่ม Cloudflare Tunnel (async — ครั้งแรกอาจต้องดาวน์โหลด cloudflared)
    tunnel_mgr = None
    try:
        if cfg.tunnel_enabled:
            from . import tunnel as tunnel_mod

            tunnel_mgr = tunnel_mod.TunnelManager(args.config)
            threading.Thread(
                target=_start_tunnel_async,
                args=(tunnel_mgr, cfg),
                daemon=True,
            ).start()
    except Exception as exc:
        log.warning("เริ่ม Cloudflare Tunnel ไม่ได้: %s", exc)

    stop_event = threading.Event()
    loop_thread = threading.Thread(
        target=ddns.run_forever,
        args=(args.config,),
        kwargs={"dry_run": False, "stop_event": stop_event},
        daemon=True,
    )
    loop_thread.start()
    try:
        while loop_thread.is_alive():
            stop_event.wait(1)
    except KeyboardInterrupt:
        print("Ctrl+C — กำลังหยุด DDNS loop...")
        stop_event.set()
        loop_thread.join(timeout=15)
    finally:
        if tunnel_mgr is not None:
            import time as _time

            _time.sleep(1.0)
            try:
                tunnel_mgr.stop()
            except Exception as exc:
                log.warning("หยุด Cloudflare Tunnel ไม่ได้: %s", exc)
        if web_ui is not None:
            try:
                web_ui.stop()
            except Exception:
                pass
    log.info("ปิด Web UI + DDNS loop + Tunnel เรียบร้อย")


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
    # subparser รับ --config เช่นกัน (หลัง subcommand) แต่ default=None กันไปทับค่า
    # ที่วางไว้หน้า subcommand (argparse จะเขียน default ทับเสมอถ้ามีค่า default)
    sub_parent = argparse.ArgumentParser(add_help=False)
    sub_parent.add_argument("--config", default=None, help=argparse.SUPPRESS)
    parser = argparse.ArgumentParser(
        prog="python -m cloudflare_ddns.main",
        description="Cloudflare DDNS Updater — Windows service สำหรับอัปเดต DNS อัตโนมัติ",
        parents=[parent],
    )
    sub = parser.add_subparsers(dest="command")

    for name in ("setup", "run", "dry-run", "install", "remove", "start", "stop", "restart", "status", "notify-test", "reset-password"):
        sub.add_parser(name, parents=[sub_parent])
    web_parser = sub.add_parser("webui", parents=[sub_parent])
    web_parser.add_argument("--port", type=int, default=None)
    web_parser.add_argument("--password", default=None)

    args = parser.parse_args(argv)
    if args.config is None:
        # ไม่มี --config ระบุ (ทั้งหน้า/หลัง) — ใช้ค่าเริ่มต้นข้าง exe/โปรแกรม
        args.config = config_mod.DEFAULT_CONFIG_PATH
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
        "reset-password": cmd_reset_password,
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

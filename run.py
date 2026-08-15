"""Runner สำหรับ PyInstaller: เข้าผ่าน package ปกติ (รองรับ relative import)."""

import sys


def run_service_entry():
    from cloudflare_ddns import service

    service.run_service_entry()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run-service":
        run_service_entry()
    else:
        from cloudflare_ddns.main import main

        main()

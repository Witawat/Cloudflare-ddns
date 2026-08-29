"""Runner สำหรับ PyInstaller: เข้าผ่าน package ปกติ (รองรับ relative import)."""

import sys
import argparse


def run_service_entry(config_path=None):
    from cloudflare_ddns import service

    return service.run_service_entry(config_path)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run-service":
        from cloudflare_ddns import config as config_mod

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--config", default=config_mod.DEFAULT_CONFIG_PATH)
        args = parser.parse_args(sys.argv[2:])
        raise SystemExit(run_service_entry(args.config) or 0)
    else:
        from cloudflare_ddns.main import main

        main()

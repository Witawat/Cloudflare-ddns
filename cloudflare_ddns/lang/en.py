"""English — flat dict (same keys as th.py)."""

EN = {
    # ---- common / 500 ----
    "err.internal": "Internal error — see the log (Log tab) for details",
    "err.internal_partial": "Internal error — see the log (Log tab) for details (some data may have been saved — please re-check)",
    "err.unauthorized": "unauthorized",
    "err.not_found": "Path not found",
    "err.csrf": "Request rejected (browser Origin does not match this page)",
    "err.json_bad": "Malformed JSON",

    # ---- login ----
    "login.locked": "Too many login attempts — temporarily locked, try again in {remain}s",
    "login.wrong": "Incorrect password",

    # ---- log ----
    "log.clear_ok": "Log cleared",
    "log.clear_fail": "Could not clear log: {exc}",
    "log.none": "(no log file yet: {exc})",

    # ---- cloudflare / token / zone ----
    "token.missing": "Token not found",
    "token.missing_bot": "Bot token not found",
    "token.missing_api": "No API token found (configure Cloudflare first)",
    "token.missing_api_dns": "No API token for DNS (configure Cloudflare first)",
    "zone.missing": "Zone not found",
    "records.none": "No A/AAAA records in this zone (will be created when an IP is found)",

    # ---- verify-token ----
    "verify.bad": "{exc}",
    "verify.no_zones": "{exc}",

    # ---- resolve-chat-id ----
    "chatid.error": "{error}",
    "chatid.notify_sent": "Sent",
    "chatid.test_default": "test",

    # ---- heartbeat-test ----
    "heartbeat.not_set": "No Healthchecks/Kuma URL configured — set it in the form first",
    "heartbeat.detail_ok": "{name}: OK",
    "heartbeat.detail_fail": "{name}: failed ({error})",

    # ---- update-check (web) ----
    "update.tunnel_latest": "cloudflared is already the latest version ({latest})",
    "update.tunnel_new": "New version available: {current} → {latest} (click 'Update cloudflared' on this page)",
    "update.tunnel_none": "cloudflared is not installed — latest version: {latest}",
    "update.check_fail": "Could not check latest version (no network?) — try again later",
    "update.no_release": "No latest release found (empty tag)",
    "update.github_err": "GitHub responded {code} (no release / rate limited)",
    "update.check_err": "Check failed: {exc}",

    # ---- port-scan ----
    "port.scan_forbidden": "Only hosts configured in config can be scanned",
    "port.bad_list": "Invalid port list (separate with commas)",
    "port.none": "No ports to scan",
    "port.resolve_fail": "Could not resolve {host}: {exc}",
    "port.detail": "{name}",

    # ---- notify-queue ----
    "queue.telegram_not_set": "Telegram is not configured in config",
    "queue.clear_ok": "Queue cleared",

    # ---- tunnel ----
    "tunnel.token_missing": "No tunnel token found",
    "tunnel.token_paste_first": "Please paste the tunnel token first",
    "tunnel.token_bad_format": "Invalid tunnel token format (should be eyJ... from the Zero Trust page)",
    "tunnel.token_no_ids": "Tunnel token has no account/tunnel id (bad format?)",
    "tunnel.api_token_no_tunnel_perm": "API token lacks Tunnel management permission (403) — go to dash.cloudflare.com → My Profile → API Tokens → Edit the token in use → add Account → Cloudflare Tunnel → Edit and try again",
    "tunnel.need_service": "Please specify a service/port, e.g. http://localhost:8080 or tcp://localhost:22",
    "tunnel.need_hostname": "Please specify a hostname, e.g. app.example.com",
    "tunnel.hostname_invalid": "Invalid hostname (must be app.example.com)",
    "tunnel.conflict": "Hostname {hostname} already has an {rtype} record (probably used for DDNS) — Cloudflare does not allow a CNAME (tunnel) sharing a name with A/AAAA — use a different name (e.g. app.example.com) or delete the existing record first",
    "tunnel.conflict_check_fail": "Could not check DNS record: {exc}",
    "tunnel.config_write_fail": "Could not write tunnel config: {error}",
    "tunnel.record_create_fail": "Could not create DNS record: {exc}",
    "tunnel.record_update": "Updated",
    "tunnel.record_create": "Created",
    "tunnel.bound_ok": "{action} record: {hostname}{path} → {tunnel_id}.cfargotunnel.com (access via https://{hostname}{path})",
    "tunnel.read_fail": "Could not read tunnel config: {error}",
    "tunnel.unbind_no_hostname": "No hostname to unbind",
    "tunnel.unbind_not_found": "{hostname}{path} not found in tunnel config",
    "tunnel.unbind_fail": "Could not remove from tunnel config: {error}",
    "tunnel.unbind_dns_fail": "Could not delete DNS record: {exc}",
    "tunnel.unbound_ok": "Unbound {hostname}{path}",
    "tunnel.unbound_ok_del_cname": "Unbound {hostname}{path} (deleted CNAME record too)",
    "tunnel.test_ok": "Token is valid — tunnel is connected to Cloudflare (stopped temporarily, waiting for final step)",
    "tunnel.test_fail": "Token check failed — cloudflared could not connect (check token/network/firewall)",
    "tunnel.sync_ok": "Synced — saved {count} hostnames to config",
    "tunnel.token_needs_setup": "No tunnel token found (set it in the form/wizard first)",

    # ---- service ----
    "service.no_admin": "No admin rights — open the web UI from a cmd/exe run as admin (or install as a service and control it from this page)",
    "service.running_inside": "This page is already running inside the service — the service is running (already installed, no need to reinstall). Use the Restart button instead (do not install over yourself: it would delete the running service and stop mid-way)",
    "service.already_installed": "Service is already installed — use Restart, or uninstall first if you want to reinstall",
    "service.install_fail": "Could not install: {exc}",
    "service.install_ok": "{message} — press Restart service to start",
    "service.not_installed": "Service is not installed",
    "service.not_installed_start": "Service is not installed — press 'Install service' first",
    "service.uninstall_running": "The service is running — uninstalling now would disconnect this page immediately (because this page runs in the service) — use uninstall.bat or run dist\\cloudflare-ddns.exe stop then remove instead",
    "service.remove_fail": "Could not uninstall: {exc}",
    "service.remove_ok": "{message}",
    "service.already_running": "Service is already running",
    "service.start_fail": "Could not start: {exc}",
    "service.start_ok": "{message}",
    "service.stop_fail": "Could not stop: {exc}",
    "service.stop_ok": "{message}",
    "service.stop_inside": "This page runs in the service — stopping now would make the page disappear and not come back (service stopped = nothing restarts it) — use dist\\cloudflare-ddns.exe stop instead",
    "service.restart_started": "Restarting service — the page will disconnect briefly and come back",

    # ---- ddns-run ----
    "ddns.busy": "A previous check is still running — wait a moment and try again",
    "ddns.running": "Checking DDNS — status will update automatically",

    # ---- open-data-folder ----
    "folder.inside_service": "This page runs in the service — cannot open the folder in your session. Copied the path for you: {path} (press Win+R → paste → Enter)",
    "folder.open_fail": "Could not open folder: {exc}",
    "folder.open_ok": "Opened the data folder ({path})",

    # ---- notify-test ----
    "notify_test.text": "✅ Test notification from Cloudflare DDNS (Web UI)",
    "notify_test.sent": "Sent — check Telegram",

    # ---- nat report (ip_detect) ----
    "nat.unknown": "Could not determine NAT status",
    "nat.cgnat_ip": "IP is in the CGNAT range (100.64.0.0/10) — your ISP shares one IP across many homes. DDNS will NOT work — use Cloudflare Tunnel or IPv6 instead",
    "nat.private_ip": "The detected IP is private — possibly behind a VPN/proxy or something is wrong. DDNS would update this IP, which outsiders cannot reach",
    "nat.cgnat_trace": "tracert shows 100.64.0.0/10 right after your WAN — you are behind your ISP's CGNAT. DDNS will NOT work — use Cloudflare Tunnel or IPv6 instead",
    "nat.double_nat": "Home NAT behind NAT ({layers} layers) — DDNS works normally",
    "nat.mismatch": "IP seen by provider ({public}) does not match what STUN sees ({stun}) — a sign the IP may be unstable / passing through multiple layers; verify yourself",
    "nat.mismatch_dyn": " and the mapped port changes every time (dynamic NAT)",
    "nat.public": "Normal public IP (no double NAT, or 1:1 NAT) — DDNS works normally (if you have a home router, remember to set up port forwarding for internal services)",
    "nat.public_symmetric": " Note: the mapped port changes every time (symmetric mapping) — set static mapping on the router for port forwarding",
    "nat.unknown_stun": "Could not reach STUN — IP is public but NAT cannot be confirmed",
}

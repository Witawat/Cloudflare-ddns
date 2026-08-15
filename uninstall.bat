@echo off
setlocal
title Cloudflare DDNS - Uninstall

rem ตรวจสิทธิ์ administrator
net session >nul 2>&1
if errorlevel 1 (
    echo [*] ขอสิทธิ์ administrator...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

if exist "dist\cloudflare-ddns.exe" (
    set "DDNS_CMD=dist\cloudflare-ddns.exe"
) else (
    set "DDNS_CMD=python -m cloudflare_ddns.main"
)

echo [1/2] ลบ service ออกจาก Windows...
%DDNS_CMD% remove
if errorlevel 1 (
    echo [x] ลบ service ล้มเหลว (service อาจยังไม่ติดตั้ง)
)

echo [2/2] เสร็จสิ้น
pause

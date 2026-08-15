@echo off
setlocal
title Cloudflare DDNS - Install

rem ตรวจสิทธิ์ administrator ถ้าไม่มีให้ relaunch เอง
net session >nul 2>&1
if errorlevel 1 (
    echo [*] ขอสิทธิ์ administrator...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

rem ถ้ามี exe ที่ build ไว้แล้ว ใช้ exe (ไม่ต้องติดตั้ง Python) ไม่มีก็ใช้ python
if exist "dist\cloudflare-ddns.exe" (
    set "DDNS_CMD=dist\cloudflare-ddns.exe"
) else (
    set "DDNS_CMD=python -m cloudflare_ddns.main"
)

if not exist "dist\cloudflare-ddns.exe" (
    echo [1/3] ติดตั้ง dependency (pywin32)...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [x] pip install ล้มเหลว
        pause
        exit /b 1
    )
)

echo [2/3] ติดตั้ง Windows Service...
%DDNS_CMD% install
if errorlevel 1 (
    echo [x] ติดตั้ง service ล้มเหลว
    pause
    exit /b 1
)

echo [3/3] เริ่ม service...
%DDNS_CMD% start

echo.
echo [+] เสร็จสิ้น - ตรวจได้ที่ services.msc หรือรัน:
echo     %DDNS_CMD% status
echo     %DDNS_CMD% webui
pause

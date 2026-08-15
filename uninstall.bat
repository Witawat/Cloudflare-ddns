@echo off
chcp 65001 >nul
setlocal
title Cloudflare DDNS - Uninstall

set "ESC="
set "GRN=%ESC%[92m"
set "RED=%ESC%[91m"
set "RST=%ESC%[0m"

rem Relaunch with admin rights if needed
net session >nul 2>&1
if errorlevel 1 (
    echo %GRN%[*]%RST% Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

rem Use the built exe when available, otherwise fall back to Python
if exist "dist\cloudflare-ddns.exe" (
    set "DDNS_CMD=dist\cloudflare-ddns.exe"
) else (
    set "DDNS_CMD=python -m cloudflare_ddns.main"
)

echo %GRN%[1/2]%RST% Removing Windows Service...
%DDNS_CMD% remove
if errorlevel 1 (
    echo %RED%[x]%RST% Remove failed ^(service may not be installed^).
)

echo %GRN%[2/2]%RST% Done.
pause

@echo off
cd /d "%~dp0.."
@echo off
setlocal ENABLEDELAYEDEXPANSION

where cloudflared >nul 2>&1
if errorlevel 1 (
    echo cloudflared не найден в PATH.
    echo Скачай его с сайта Cloudflare и добавь в PATH.
    pause
    exit /b 1
)

echo Запуск Cloudflare Quick Tunnel для http://127.0.0.1:8080
cloudflared tunnel --url http://127.0.0.1:8080 > var\logs\cloudflare_quick_manual.log 2>&1

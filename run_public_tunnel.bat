@echo off
title ClauseVerify AI — Public Cloudflare Tunnel Launcher
echo ============================================================
echo   ClauseVerify AI — Public Cloudflare Gateway Launcher
echo ============================================================

echo Starting local Uvicorn ASGI server in background...
start /B "" "C:\Users\Yasir\AppData\Local\Python\bin\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000

timeout /t 2 /nobreak >nul

echo Starting Cloudflare Secure Public Tunnel...
echo ------------------------------------------------------------
echo Look below for your generated public HTTPS link:
echo ------------------------------------------------------------
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8000
) else (
    cloudflared tunnel --url http://127.0.0.1:8000
)
pause

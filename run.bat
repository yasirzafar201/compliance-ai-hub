@echo off
title ClauseVerify AI — Enterprise Production Server
echo ============================================================
echo   ClauseVerify AI — Enterprise Production Server
echo ============================================================
echo [1/3] Checking dependencies...
if exist "C:\Users\Yasir\AppData\Local\Python\bin\python.exe" (
    set "PY_BIN=C:\Users\Yasir\AppData\Local\Python\bin\python.exe"
) else (
    set "PY_BIN=python"
)

echo [2/3] Launching Web Browser at http://localhost:8000 ...
start "" http://localhost:8000

echo [3/3] Starting High-Performance ASGI Engine (Uvicorn)...
echo ------------------------------------------------------------
echo Local Dashboard:  http://localhost:8000
echo Swagger API Docs: http://localhost:8000/docs
echo ------------------------------------------------------------
echo Press CTRL+C to stop the server.

%PY_BIN% -m uvicorn app:app --host 127.0.0.1 --port 8000
pause

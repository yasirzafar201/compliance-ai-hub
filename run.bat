@echo off
echo ============================================================
echo   ClauseVerify AI — Enterprise FastAPI Production Server
echo ============================================================
echo Starting async Uvicorn server on http://localhost:8000 ...
echo Swagger API Docs: http://localhost:8000/docs

start "" http://localhost:8000

if exist "C:\Users\Yasir\AppData\Local\Python\bin\python.exe" (
    "C:\Users\Yasir\AppData\Local\Python\bin\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000
) else (
    python -m uvicorn app:app --host 127.0.0.1 --port 8000
)
pause

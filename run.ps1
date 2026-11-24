Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ClauseVerify AI — Enterprise FastAPI Production Server" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting async Uvicorn server on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "Interactive Swagger API Docs available at: http://localhost:8000/docs" -ForegroundColor Magenta

Start-Process "http://localhost:8000"

$pythonExe = "C:\Users\Yasir\AppData\Local\Python\bin\python.exe"
if (Test-Path $pythonExe) {
    & $pythonExe -m uvicorn app:app --host 127.0.0.1 --port 8000
} else {
    python -m uvicorn app:app --host 127.0.0.1 --port 8000
}

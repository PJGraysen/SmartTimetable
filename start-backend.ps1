# start-backend.ps1
# Starts the Django/Daphne dev server on port 8000.
# Uses the venv at .venv if present.

$ErrorActionPreference = "Stop"
Set-Location "C:\Projects\SmartTimetable\backend"

# Activate venv if present
$venv = "C:\Projects\SmartTimetable\.venv\Scripts\Activate.ps1"
if (Test-Path $venv) { & $venv }

Write-Host ""
Write-Host "=== SMARTTIMETABLE BACKEND ===" -ForegroundColor Cyan

python manage.py check
if ($LASTEXITCODE -ne 0) {
    throw "Django check failed. Backend will not start."
}

# Guard against port collision
$existing = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[warn] Port 8000 already in use by PID $($existing.OwningProcess)." -ForegroundColor Yellow
    Write-Host "[warn] If this is a stale backend, stop it first with: Stop-Process -Id <PID>" -ForegroundColor Yellow
    exit 1
}

python manage.py runserver 127.0.0.1:8000

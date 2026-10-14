# start-frontend.ps1
# Starts the Vite dev server for the frontend.

$ErrorActionPreference = "Stop"
Set-Location "C:\Projects\SmartTimetable\frontend"

Write-Host ""
Write-Host "=== SMARTTIMETABLE FRONTEND ===" -ForegroundColor Cyan

npm run dev

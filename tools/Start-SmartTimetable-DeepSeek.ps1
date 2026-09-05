$ErrorActionPreference = "Stop"

$Project = "C:\Projects\SmartTimetable"
$Model = "deepseek-coder:1.3b"
$Context = 4096
$KeepAlive = "30s"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SMARTTIMETABLE — LOW-RAM LOCAL DEEPSEEK" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $Project

Write-Host "Project : $Project" -ForegroundColor Yellow
Write-Host "Model   : $Model" -ForegroundColor Yellow
Write-Host "Context : $Context tokens" -ForegroundColor Yellow
Write-Host "Unload  : $KeepAlive" -ForegroundColor Yellow

Write-Host ""
Write-Host "Ollama:" -ForegroundColor Yellow
ollama --version

Write-Host ""
Write-Host "Checking model..." -ForegroundColor Yellow

& ollama show $Model *> $null

if ($LASTEXITCODE -ne 0) {
    throw "Required local model is unavailable: $Model"
}

Write-Host "Model detected." -ForegroundColor Green

Write-Host ""
Write-Host "Checking available RAM..." -ForegroundColor Yellow

$os = Get-CimInstance Win32_OperatingSystem

$freeGB = [math]::Round(
    ($os.FreePhysicalMemory * 1KB) / 1GB,
    2
)

Write-Host "Free RAM: $freeGB GB" -ForegroundColor Yellow

if ($freeGB -lt 0.20) {
    Write-Host ""
    Write-Host "RAM is critically low." -ForegroundColor Red
    Write-Host "DeepSeek will not be started." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting local DeepSeek Coder..." -ForegroundColor Green
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Model      : $Model"
Write-Host "  Context    : $Context"
Write-Host "  Keep alive : $KeepAlive"
Write-Host "  Provider   : Ollama localhost"
Write-Host "  Cloud      : NONE"
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " LOCAL DEEPSEEK READY" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Type /bye when finished." -ForegroundColor DarkGray
Write-Host ""

ollama run $Model --keepalive $KeepAlive


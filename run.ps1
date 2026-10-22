# OceanGuard AI One-Click Launcher for PowerShell
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\backend"

$pythonExe = "C:\Users\Poojitha\AppData\Local\Programs\Python311\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$env:PYTHONPATH = (Get-Location).Path
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  OceanGuard AI - Marine Pollution Monitoring & Investigation System" -ForegroundColor White
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "Using Python: $pythonExe" -ForegroundColor Green
Write-Host "Working Directory: $env:PYTHONPATH" -ForegroundColor Green
Write-Host ""
Write-Host "Opening web browser at http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:8000"

Write-Host "Starting Uvicorn web server..." -ForegroundColor Cyan
Write-Host "(Press Ctrl+C to stop the server)" -ForegroundColor Gray
& $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

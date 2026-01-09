$ErrorActionPreference = "Stop"

Write-Host "Automation Hub Windows setup"

$pythonVersion = (& python --version 2>&1)
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python not found. Install Python 3.11+ and ensure it is on PATH." -ForegroundColor Red
    exit 1
}
Write-Host "Python detected: $pythonVersion"

$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
    Write-Host "adb not found. Install Android platform-tools and add adb to PATH." -ForegroundColor Red
    exit 1
}
Write-Host "adb detected: $($adb.Source)"

$devices = & adb devices
Write-Host $devices
if ($devices -notmatch "\tdevice") {
    Write-Host "No connected devices detected. Plug in the device and enable USB debugging." -ForegroundColor Yellow
}

if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

if (-not (Test-Path "config.local.env")) {
    Copy-Item "config.example.env" "config.local.env"
    Write-Host "Created config.local.env from template. Update it with your settings." -ForegroundColor Yellow
}

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1) Update config.local.env with your phone number, allowed senders, and device id if needed."
Write-Host "2) Run: python -m automation_hub doctor"
Write-Host "3) Run: python -m automation_hub run"

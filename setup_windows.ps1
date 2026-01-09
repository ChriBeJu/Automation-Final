$ErrorActionPreference = "Stop"

Write-Host "Automation Hub Windows setup"

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        return ""
    }

    $match = Select-String -Path $Path -Pattern "^$Key=(.*)$" | Select-Object -First 1
    if ($match) {
        return $match.Matches[0].Groups[1].Value
    }

    return ""
}

function Set-EnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    if (-not (Test-Path $Path)) {
        return
    }

    $updated = $false
    $lines = Get-Content $Path | ForEach-Object {
        if ($_ -match "^$Key=") {
            $updated = $true
            "$Key=$Value"
        } else {
            $_
        }
    }

    if (-not $updated) {
        $lines += "$Key=$Value"
    }

    Set-Content -Path $Path -Value $lines
}

$pythonVersion = (& python --version 2>&1)
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python not found. Install Python 3.11+ and ensure it is on PATH." -ForegroundColor Red
    exit 1
}
Write-Host "Python detected: $pythonVersion"

$adbCommand = $null
$adb = Get-Command adb -ErrorAction SilentlyContinue
if ($adb) {
    $adbCommand = "adb"
    Write-Host "adb detected on PATH: $($adb.Source)"
} else {
    Write-Host "adb not found. Downloading Android platform-tools..." -ForegroundColor Yellow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $toolsDir = Join-Path $PSScriptRoot "tools"
    $platformToolsDir = Join-Path $toolsDir "platform-tools"
    $adbPath = Join-Path $platformToolsDir "adb.exe"
    if (-not (Test-Path $adbPath)) {
        if (-not (Test-Path $toolsDir)) { New-Item -ItemType Directory -Path $toolsDir | Out-Null }
        $zipPath = Join-Path $toolsDir "platform-tools.zip"
        Invoke-WebRequest -Uri "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -OutFile $zipPath
        if (Test-Path $platformToolsDir) {
            Remove-Item -Recurse -Force $platformToolsDir
        }
        Expand-Archive -Path $zipPath -DestinationPath $toolsDir
        Remove-Item $zipPath
    }

    if (-not (Test-Path $adbPath)) {
        Write-Host "Failed to download adb. Install Android platform-tools manually and add adb to PATH." -ForegroundColor Red
        exit 1
    }

    $adbCommand = $adbPath
    Write-Host "adb downloaded to $adbPath"
}

$devices = & $adbCommand devices
Write-Host $devices
if ($devices -notmatch "\tdevice") {
    Write-Host "No connected devices detected. Plug in the device and enable USB debugging." -ForegroundColor Yellow
}

if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

if (-not (Test-Path "config.local.env")) {
    Copy-Item "config.example.env" "config.local.env"
    Write-Host "Created config.local.env from template. We'll now fill in the essentials." -ForegroundColor Yellow
}

$adbConfigValue = if ($adbCommand -eq "adb") { "adb" } else { "tools/platform-tools/adb.exe" }
Set-EnvValue -Path "config.local.env" -Key "ADB_PATH" -Value $adbConfigValue

$smsForwardDefault = Get-EnvValue -Path "config.local.env" -Key "SMS_FORWARD_NUMBER"
$smsForwardInput = Read-Host "SMS forward number (example +15551234567) [${smsForwardDefault}]"
if ([string]::IsNullOrWhiteSpace($smsForwardInput)) {
    $smsForwardInput = $smsForwardDefault
}
Set-EnvValue -Path "config.local.env" -Key "SMS_FORWARD_NUMBER" -Value $smsForwardInput

$allowedSendersDefault = Get-EnvValue -Path "config.local.env" -Key "ALLOWED_SMS_SENDERS"
$allowedSendersInput = Read-Host "Allowed SMS senders (comma-separated) [${allowedSendersDefault}]"
if ([string]::IsNullOrWhiteSpace($allowedSendersInput)) {
    $allowedSendersInput = $allowedSendersDefault
}
Set-EnvValue -Path "config.local.env" -Key "ALLOWED_SMS_SENDERS" -Value $allowedSendersInput

$deviceIdDefault = Get-EnvValue -Path "config.local.env" -Key "ADB_DEVICE_ID"
$deviceIdInput = Read-Host "ADB device id (leave blank to auto-select) [${deviceIdDefault}]"
if ([string]::IsNullOrWhiteSpace($deviceIdInput)) {
    $deviceIdInput = $deviceIdDefault
}
Set-EnvValue -Path "config.local.env" -Key "ADB_DEVICE_ID" -Value $deviceIdInput

Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1) Run: python -m automation_hub doctor"
Write-Host "2) Run: python -m automation_hub run"

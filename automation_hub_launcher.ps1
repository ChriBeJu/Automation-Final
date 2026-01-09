param(
    [ValidateSet("setup", "doctor", "run", "tail")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$env:PYTHONPATH = "$repoRoot/src;$env:PYTHONPATH"

function Test-Python {
    $pythonVersion = (& python --version 2>&1)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Python not found. Install Python 3.11+ and ensure it is on PATH." -ForegroundColor Red
        return $false
    }
    Write-Host "Python detected: $pythonVersion"
    return $true
}

function Test-AdbAvailable {
    $adb = Get-Command adb -ErrorAction SilentlyContinue
    if ($adb) {
        return $true
    }

    $adbPath = Join-Path $repoRoot "tools/platform-tools/adb.exe"
    return (Test-Path $adbPath)
}

function Ensure-Setup {
    if (-not (Test-Python)) {
        throw "Python missing"
    }

    $configPath = Join-Path $repoRoot "config.local.env"
    $needsSetup = -not (Test-Path $configPath)
    if (-not (Test-AdbAvailable)) {
        $needsSetup = $true
    }

    if ($needsSetup) {
        & (Join-Path $repoRoot "setup_windows.ps1")
    }
}

function Invoke-Doctor {
    Ensure-Setup
    & python -m automation_hub doctor
}

function Invoke-Run {
    Ensure-Setup
    & python -m automation_hub run
}

function Invoke-Tail {
    $logPath = Join-Path $repoRoot "logs/automation_hub.log"
    if (-not (Test-Path $logPath)) {
        Write-Host "Log file not found yet: $logPath" -ForegroundColor Yellow
        return
    }

    Get-Content -Path $logPath -Wait -Tail 200
}

if ($Mode) {
    switch ($Mode) {
        "setup" { & (Join-Path $repoRoot "setup_windows.ps1") }
        "doctor" { Invoke-Doctor }
        "run" { Invoke-Run }
        "tail" { Invoke-Tail }
    }
    exit 0
}
Write-Host "Usage: powershell -ExecutionPolicy Bypass -File automation_hub_launcher.ps1 -Mode <setup|doctor|run|tail>" -ForegroundColor Yellow
exit 1

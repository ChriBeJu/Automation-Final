param(
    [ValidateSet("setup", "doctor", "run", "tail")]
    [string]$Mode,
    [switch]$Gui
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

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

function Start-LoggedProcess {
    param(
        [string]$FileName,
        [string]$Arguments,
        [scriptblock]$OnOutput
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FileName
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $repoRoot
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    $process.EnableRaisingEvents = $true

    $outputHandler = {
        param($sender, $args)
        if ($args.Data) {
            & $OnOutput $args.Data
        }
    }

    $process.add_OutputDataReceived($outputHandler)
    $process.add_ErrorDataReceived($outputHandler)

    [void]$process.Start()
    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()

    return $process
}

function Show-Gui {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Automation Hub Launcher"
    $form.Size = New-Object System.Drawing.Size(900, 600)
    $form.StartPosition = "CenterScreen"

    $buttonSetup = New-Object System.Windows.Forms.Button
    $buttonSetup.Text = "Setup"
    $buttonSetup.Location = New-Object System.Drawing.Point(20, 20)
    $buttonSetup.Size = New-Object System.Drawing.Size(100, 30)

    $buttonDoctor = New-Object System.Windows.Forms.Button
    $buttonDoctor.Text = "Doctor"
    $buttonDoctor.Location = New-Object System.Drawing.Point(130, 20)
    $buttonDoctor.Size = New-Object System.Drawing.Size(100, 30)

    $buttonRun = New-Object System.Windows.Forms.Button
    $buttonRun.Text = "Run"
    $buttonRun.Location = New-Object System.Drawing.Point(240, 20)
    $buttonRun.Size = New-Object System.Drawing.Size(100, 30)

    $buttonStop = New-Object System.Windows.Forms.Button
    $buttonStop.Text = "Stop"
    $buttonStop.Location = New-Object System.Drawing.Point(350, 20)
    $buttonStop.Size = New-Object System.Drawing.Size(100, 30)

    $buttonTail = New-Object System.Windows.Forms.Button
    $buttonTail.Text = "Tail Logs"
    $buttonTail.Location = New-Object System.Drawing.Point(460, 20)
    $buttonTail.Size = New-Object System.Drawing.Size(100, 30)

    $textBox = New-Object System.Windows.Forms.TextBox
    $textBox.Location = New-Object System.Drawing.Point(20, 70)
    $textBox.Size = New-Object System.Drawing.Size(840, 470)
    $textBox.Multiline = $true
    $textBox.ScrollBars = "Vertical"
    $textBox.ReadOnly = $true

    $form.Controls.AddRange(@($buttonSetup, $buttonDoctor, $buttonRun, $buttonStop, $buttonTail, $textBox))

    $script:runProcess = $null
    $script:tailProcess = $null

    $appendOutput = {
        param([string]$line)
        $form.BeginInvoke([action]{
            $textBox.AppendText($line + [Environment]::NewLine)
        }) | Out-Null
    }

    $buttonSetup.Add_Click({
        try {
            $appendOutput.Invoke("Running setup...")
            & (Join-Path $repoRoot "setup_windows.ps1")
            $appendOutput.Invoke("Setup completed.")
        } catch {
            $appendOutput.Invoke("Setup failed: $($_.Exception.Message)")
        }
    })

    $buttonDoctor.Add_Click({
        try {
            $appendOutput.Invoke("Running doctor...")
            Ensure-Setup
            & python -m automation_hub doctor | ForEach-Object { $appendOutput.Invoke($_) }
        } catch {
            $appendOutput.Invoke("Doctor failed: $($_.Exception.Message)")
        }
    })

    $buttonRun.Add_Click({
        if ($script:runProcess -and -not $script:runProcess.HasExited) {
            $appendOutput.Invoke("Run already in progress.")
            return
        }

        try {
            $appendOutput.Invoke("Starting automation hub...")
            Ensure-Setup
            $script:runProcess = Start-LoggedProcess -FileName "python" -Arguments "-m automation_hub run" -OnOutput $appendOutput
        } catch {
            $appendOutput.Invoke("Run failed: $($_.Exception.Message)")
        }
    })

    $buttonStop.Add_Click({
        if ($script:runProcess -and -not $script:runProcess.HasExited) {
            $appendOutput.Invoke("Stopping automation hub...")
            $script:runProcess.Kill()
            $script:runProcess = $null
        }
        if ($script:tailProcess -and -not $script:tailProcess.HasExited) {
            $appendOutput.Invoke("Stopping log tail...")
            $script:tailProcess.Kill()
            $script:tailProcess = $null
        }
    })

    $buttonTail.Add_Click({
        if ($script:tailProcess -and -not $script:tailProcess.HasExited) {
            $appendOutput.Invoke("Log tail already running.")
            return
        }

        $logPath = Join-Path $repoRoot "logs/automation_hub.log"
        if (-not (Test-Path $logPath)) {
            $appendOutput.Invoke("Log file not found yet: $logPath")
            return
        }

        $appendOutput.Invoke("Tailing logs...")
        $script:tailProcess = Start-LoggedProcess -FileName "powershell" -Arguments "-NoProfile -Command \"Get-Content -Path '$logPath' -Wait -Tail 200\"" -OnOutput $appendOutput
    })

    $form.Add_FormClosing({
        if ($script:runProcess -and -not $script:runProcess.HasExited) {
            $script:runProcess.Kill()
        }
        if ($script:tailProcess -and -not $script:tailProcess.HasExited) {
            $script:tailProcess.Kill()
        }
    })

    [void]$form.ShowDialog()
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

if ($Gui -or -not $Mode) {
    Show-Gui
}

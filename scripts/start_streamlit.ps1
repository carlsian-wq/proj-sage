# start_streamlit.ps1
# Starts only the Project Sage Streamlit server (console stays open).
# Used by the "Project Sage Streamlit" desktop shortcut.
#
#   powershell -ExecutionPolicy Bypass -File scripts\start_streamlit.ps1

param(
    [int]$Port = 8504
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "data"
$LogFile = Join-Path $LogDir "streamlit.log"
$Url = "http://localhost:$Port"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

function Write-StreamlitLog([string]$Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    try {
        Add-Content -Path $LogFile -Value $line -Encoding utf8
    } catch {
        # ignore
    }
}

if (-not (Test-Path $Python)) {
    Write-Host "Python venv not found: $Python"
    Write-Host "Create .venv and install requirements (see README)."
    exit 1
}

function Write-LoggedLine([string]$Line) {
    if ($null -eq $Line) { return }
    Write-Host $Line
    try {
        Add-Content -Path $LogFile -Value $Line -Encoding utf8
    } catch {
        # ignore
    }
}

function Test-ServerUp([string]$BaseUrl) {
    try {
        $resp = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 2
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
    } catch {
        return $false
    }
}

if (Test-ServerUp $Url) {
    Write-Host "Project Sage is already running at $Url" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  show_running:  .\scripts\show_running.ps1"
    Write-Host "  stop server:   .\scripts\stop_project_sage.ps1"
    Write-Host "  server log:    data\streamlit.log"
    Write-Host ""
    Write-Host "This window stays open so you can read the message."
    Write-Host "Press Enter to close (server keeps running)."
    Read-Host
    exit 0
}

Set-Location -LiteralPath $ProjectRoot
Write-Host "Starting Project Sage Streamlit on $Url"
Write-Host "Logging to data\streamlit.log (and this console)."
Write-Host "Close this window to stop the server."
Write-Host ""

Write-StreamlitLog "===== Streamlit start (port $Port) ====="
$env:PYTHONFAULTHANDLER = "1"

# Streamlit logs normal startup lines to stderr. Merge streams and print as
# plain text so PowerShell does not show scary NativeCommandError blocks.
$exit = 0
try {
    & $Python -m streamlit run app.py --server.port $Port 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) {
            Write-LoggedLine($_.ToString())
        } else {
            Write-LoggedLine("$_")
        }
    }
    if ($null -ne $LASTEXITCODE) {
        $exit = $LASTEXITCODE
    }
} catch {
    Write-StreamlitLog "FATAL: $($_.Exception.Message)"
    Write-Host $_.Exception.Message -ForegroundColor Red
    $exit = 1
}

Write-StreamlitLog "===== Streamlit exited (code $exit) ====="
Write-Host ""
if ($exit -ne 0) {
    Write-Host "Streamlit stopped with exit code $exit." -ForegroundColor Yellow
} else {
    Write-Host "Streamlit stopped (exit code $exit)."
}
Write-Host "Logs: data\streamlit.log | data\crash.log | data\faulthandler.log"
Write-Host "Press Enter to close this window."
Read-Host | Out-Null
exit $exit
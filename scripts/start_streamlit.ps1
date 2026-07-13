# start_streamlit.ps1
# Starts only the Project Sage Streamlit server (console stays open).
# Used by the "Project Sage Streamlit" desktop shortcut.
#
#   powershell -ExecutionPolicy Bypass -File scripts\start_streamlit.ps1

param(
    [int]$Port = 8504
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Streamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"
$Url = "http://localhost:$Port"

if (-not (Test-Path $Streamlit)) {
    Write-Host "Streamlit not found: $Streamlit"
    Write-Host "Create .venv and install requirements (see README)."
    exit 1
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
    Write-Host ""
    Write-Host "This window stays open so you can read the message."
    Write-Host "Press Enter to close (server keeps running)."
    Read-Host
    exit 0
}

Set-Location -LiteralPath $ProjectRoot
Write-Host "Starting Project Sage Streamlit on $Url"
Write-Host "Close this window to stop the server."
Write-Host ""
& $Streamlit run app.py --server.port $Port

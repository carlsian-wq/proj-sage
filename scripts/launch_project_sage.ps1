# launch_project_sage.ps1
# Starts Project Sage (Streamlit) and opens Chrome/Edge in app mode (no browser tabs).
#
# Double-click "Project Sage.lnk" on your Desktop, or run:
#   powershell -ExecutionPolicy Bypass -File scripts\launch_project_sage.ps1

param(
    [int]$Port = 8504,
    [string]$Browser = "chrome"
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Streamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "data"
$LogFile = Join-Path $LogDir "launcher.log"
$Url = "http://localhost:$Port"

function Write-LauncherLog([string]$Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    try {
        if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
        Add-Content -Path $LogFile -Value $line -Encoding utf8
    } catch {
        # ignore logging failures
    }
}

function Test-ServerUp([string]$BaseUrl) {
    try {
        $resp = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 3
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Wait-ForServer([string]$BaseUrl, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-ServerUp $BaseUrl) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Resolve-Browser([string]$Preference) {
    $chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
    $chromeLocal = Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe"
    $edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    $edge64 = "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"

    if ($Preference -eq "edge") {
        if (Test-Path $edge64) { return $edge64 }
        if (Test-Path $edge) { return $edge }
    }
    if (Test-Path $chrome) { return $chrome }
    if (Test-Path $chromeLocal) { return $chromeLocal }
    if (Test-Path $edge64) { return $edge64 }
    if (Test-Path $edge) { return $edge }
    return $null
}

function Test-OllamaApi {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

function Ensure-OllamaServer {
    if (Test-OllamaApi) {
        Write-LauncherLog "Ollama API already up on :11434"
        return $true
    }
    $ollamaCli = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (-not (Test-Path $ollamaCli)) {
        Write-LauncherLog "WARN: Ollama not installed; RAG answers will fail until it is running"
        return $false
    }
    Write-LauncherLog "Starting ollama serve"
    Start-Process -FilePath $ollamaCli -ArgumentList @("serve") -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-OllamaApi) {
            Write-LauncherLog "Ollama API ready"
            return $true
        }
        Start-Sleep -Seconds 2
    }
    Write-LauncherLog "WARN: Ollama API did not respond within 45s"
    return $false
}

Ensure-OllamaServer | Out-Null

if (-not (Test-Path $Streamlit)) {
    $msg = "Streamlit not found: $Streamlit`nRun setup from README (create .venv and pip install -r requirements.txt)."
    Write-LauncherLog "ERROR: $msg"
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue | Out-Null
        [System.Windows.Forms.MessageBox]::Show($msg, "Project Sage", 0, 16) | Out-Null
    } catch {
        Write-Host $msg
    }
    exit 1
}

$alreadyRunning = Test-ServerUp $Url

if (-not $alreadyRunning) {
    Write-LauncherLog "Starting Streamlit on port $Port"
    $streamlitCmd = "& '$Streamlit' run app.py --server.port $Port --server.headless true"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "Set-Location -LiteralPath '$ProjectRoot'; Write-Host 'Project Sage Streamlit server (port $Port). Close this window to stop the server.'; $streamlitCmd"
    ) -WorkingDirectory $ProjectRoot
    if (-not (Wait-ForServer $Url)) {
        $msg = "Project Sage did not start within 60 seconds. Check the Streamlit console for errors."
        Write-LauncherLog "ERROR: $msg"
        try {
            Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue | Out-Null
            [System.Windows.Forms.MessageBox]::Show($msg, "Project Sage", 0, 16) | Out-Null
        } catch {
            Write-Host $msg
        }
        exit 1
    }
} else {
    Write-LauncherLog "Server already running on $Url"
}

$browserExe = Resolve-Browser $Browser
if (-not $browserExe) {
    Write-LauncherLog "Browser not found; opening default browser"
    Start-Process $Url
    exit 0
}

$browserName = Split-Path $browserExe -Leaf
Write-LauncherLog "Opening $browserName app window: $Url"
Start-Process -FilePath $browserExe -ArgumentList @(
    "--app=$Url",
    "--new-window",
    "--window-size=1440,900",
    "--window-position=80,40"
)

Write-LauncherLog "Launch complete"
exit 0

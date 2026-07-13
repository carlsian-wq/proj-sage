# install_desktop_shortcuts.ps1
# Creates Desktop shortcuts for Project Sage with the project logo icon:
#   1) Project Sage           — start server (if needed) + open Chrome/Edge app window
#   2) Project Sage Streamlit — Streamlit server console only
#
# Run:
#   powershell -ExecutionPolicy Bypass -File scripts\install_desktop_shortcuts.ps1
#
# Optional:
#   -Browser edge     # prefer Edge for the app-mode launcher (default: chrome)

param(
    [ValidateSet("chrome", "edge")]
    [string]$Browser = "chrome"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LauncherPs1 = Join-Path $ProjectRoot "scripts\launch_project_sage.ps1"
$ServerPs1 = Join-Path $ProjectRoot "scripts\start_streamlit.ps1"
$BuildIcon = Join-Path $ProjectRoot "scripts\build_icon.py"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Icon = Join-Path $ProjectRoot "assets\logo.ico"
$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path $LauncherPs1)) {
    Write-Error "Launcher not found: $LauncherPs1"
}
if (-not (Test-Path $ServerPs1)) {
    Write-Error "Server script not found: $ServerPs1"
}

# Build multi-resolution .ico from assets/logo.jpg
if (Test-Path $Python) {
    if (Test-Path $BuildIcon) {
        & $Python $BuildIcon
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Icon build failed; shortcuts may use a default icon."
        }
    }
} else {
    Write-Warning "Project venv Python not found; skip icon rebuild."
}

$shell = New-Object -ComObject WScript.Shell

function New-SageShortcut {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [Parameter(Mandatory = $true)][string]$Description,
        [string]$ExtraArgs = ""
    )
    $path = Join-Path $Desktop "$Name.lnk"
    $sc = $shell.CreateShortcut($path)
    $sc.TargetPath = $PowerShellExe
    # Do not use $args — it is a PowerShell automatic variable.
    # -NoExit keeps the console visible (Streamlit server or launcher messages).
    $argLine = "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
    if ($ExtraArgs) {
        $argLine = "$argLine $ExtraArgs"
    }
    $sc.Arguments = $argLine
    $sc.WorkingDirectory = $ProjectRoot
    $sc.WindowStyle = 1
    $sc.Description = $Description
    if (Test-Path $Icon) {
        $sc.IconLocation = "$Icon,0"
    }
    $sc.Save()
    Write-Host "  $path"
}

Write-Host "Creating Desktop shortcuts (icon: $Icon)..." -ForegroundColor Cyan

New-SageShortcut -Name "Project Sage" -ScriptPath $LauncherPs1 `
    -Description "Project Sage - Streamlit + Chrome/Edge desktop web app" `
    -ExtraArgs "-Browser $Browser"

New-SageShortcut -Name "Project Sage Streamlit" -ScriptPath $ServerPs1 `
    -Description "Project Sage - Streamlit server only (startup console)"

Write-Host ""
Write-Host "Desktop shortcuts ready:" -ForegroundColor Green
Write-Host "  Project Sage            - starts server if needed, opens $Browser --app mode"
Write-Host "  Project Sage Streamlit  - Streamlit console on http://localhost:8504"
Write-Host ""
Write-Host "Logo icon: assets\logo.ico"
Write-Host "Re-run this script anytime to refresh shortcuts/icon."

# Streamlit dashboard status — all Sage-family apps on the local port map.
# Usage: .\scripts\show_running.ps1
#        .\scripts\show_running.ps1 -Details   # include process chains

param(
    [switch]$Details
)

$ErrorActionPreference = "SilentlyContinue"

$Apps = @(
    @{ Port = 8501; Name = "hyperliquid-bot"; Label = "Trading dashboard" }
    @{ Port = 8502; Name = "log-sage";        Label = "Log Sage" }
    @{ Port = 8503; Name = "net-comd-comp";   Label = "net-comd-comp" }
    @{ Port = 8504; Name = "proj-sage";      Label = "Project Sage" }
)

function Get-ListenPid([int]$ListenPort) {
    $conn = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($conn) { return [int]$conn.OwningProcess }
    return 0
}

function Get-ProcessInfo([int]$ProcessId) {
    if ($ProcessId -le 0) { return $null }
    return Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
}

function Get-ShortCmd([string]$Cmd, [int]$Max = 88) {
    if (-not $Cmd) { return "" }
    if ($Cmd.Length -le $Max) { return $Cmd }
    return $Cmd.Substring(0, $Max) + "..."
}

function Get-ProcessChain([int]$LeafPid) {
    $nodes = [System.Collections.Generic.List[object]]::new()
    $seen = @{}
    $current = $LeafPid
    while ($current -gt 0 -and -not $seen.ContainsKey($current)) {
        $seen[$current] = $true
        $p = Get-ProcessInfo $current
        if (-not $p) { break }
        $nodes.Add($p) | Out-Null
        $current = [int]$p.ParentProcessId
        # Stop climbing at unrelated system processes
        if ($p.Name -in @("services.exe", "svchost.exe", "wininit.exe")) { break }
    }
    return $nodes
}

function Get-StopHint([int]$Port) {
    switch ($Port) {
        8501 { return "hyperliquid-bot: close dashboard Streamlit console or end PID on :8501" }
        8502 { return "log-sage: .\scripts\stop_log_sage.ps1 (in log-sage repo) or close its console" }
        8503 { return "net-comd-comp: close its Streamlit console or end PID on :8503" }
        8504 { return "proj-sage: .\scripts\stop_project_sage.ps1 or close Project Sage Streamlit console" }
        default { return "" }
    }
}

Write-Host ""
Write-Host "  Streamlit apps on this PC (one row = one app)" -ForegroundColor Cyan
Write-Host "  ---------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

$running = 0
foreach ($app in $Apps) {
    $listenPid = Get-ListenPid $app.Port
    $url = "http://localhost:$($app.Port)"
    if ($listenPid -gt 0) {
        $running++
        Write-Host ("  :{0}  {1,-22} RUNNING   PID {2}" -f $app.Port, $app.Label, $listenPid) -ForegroundColor Green
        Write-Host ("         {0}" -f $url) -ForegroundColor DarkGray
    } else {
        Write-Host ("  :{0}  {1,-22} stopped" -f $app.Port, $app.Label) -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "  Summary: $running of $($Apps.Count) apps running" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Note: Windows uses 3-4 PIDs per app (powershell -> streamlit -> python)." -ForegroundColor DarkGray
Write-Host "        That is ONE instance, not duplicates." -ForegroundColor DarkGray
Write-Host ""

if ($Details) {
    Write-Host "  Process chains (listener PID and parents):" -ForegroundColor Cyan
    Write-Host ""
    foreach ($app in $Apps) {
        $listenPid = Get-ListenPid $app.Port
        if ($listenPid -le 0) { continue }
        Write-Host "  $($app.Label) (:$($app.Port))" -ForegroundColor White
        foreach ($node in (Get-ProcessChain $listenPid)) {
            Write-Host ("    PID {0,-7} {1,-14} {2}" -f $node.ProcessId, $node.Name, (Get-ShortCmd $node.CommandLine))
        }
        Write-Host ""
    }
}

$projListenPid = Get-ListenPid 8504
if ($projListenPid -gt 0) {
    Write-Host "  Stop Project Sage: .\scripts\stop_project_sage.ps1" -ForegroundColor DarkGray
} else {
    Write-Host "  Start Project Sage: .\scripts\start_streamlit.ps1" -ForegroundColor DarkGray
    Write-Host "                      or desktop shortcut 'Project Sage Streamlit'" -ForegroundColor DarkGray
}
Write-Host "  More detail:        .\scripts\show_running.ps1 -Details" -ForegroundColor DarkGray
Write-Host ""
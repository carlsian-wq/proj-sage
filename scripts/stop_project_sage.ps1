# Stop Project Sage Streamlit (port 8504) and related parent shells.
# Usage: .\scripts\stop_project_sage.ps1

$ErrorActionPreference = "SilentlyContinue"
$Port = 8504

function Stop-Tree([int]$RootPid, [hashtable]$Stopped) {
    if ($RootPid -le 0 -or $Stopped.ContainsKey($RootPid)) { return }
    $children = Get-CimInstance Win32_Process |
        Where-Object { $_.ParentProcessId -eq $RootPid } |
        ForEach-Object { [int]$_.ProcessId }
    foreach ($c in $children) { Stop-Tree $c $Stopped }
    $Stopped[$RootPid] = $true
    $p = Get-Process -Id $RootPid -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "Stopping PID $RootPid ($($p.ProcessName))"
        Stop-Process -Id $RootPid -Force -ErrorAction SilentlyContinue
    }
}

$listenPids = @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    Where-Object { $_ -gt 0 })

if (-not $listenPids.Count) {
    Write-Host "No process listening on port $Port."
    # Clean stray proj-sage streamlit workers
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match 'proj-sage.*app\.py|proj-sage.*streamlit' } |
        ForEach-Object {
            Write-Host "Stopping stray PID $($_.ProcessId)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    exit 0
}

$stopped = @{}
foreach ($lp in $listenPids) {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$lp" -ErrorAction SilentlyContinue
    if ($p) {
        Stop-Tree ([int]$p.ParentProcessId) $stopped
        Stop-Tree $lp $stopped
    }
}

Start-Sleep -Seconds 1
$still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Host "Port $Port still in use - run show_running.ps1 and end remaining PIDs in Task Manager." -ForegroundColor Yellow
} else {
    Write-Host "Project Sage stopped (port $Port free)." -ForegroundColor Green
}
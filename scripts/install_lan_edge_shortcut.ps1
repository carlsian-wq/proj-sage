# install_lan_edge_shortcut.ps1
# Edge app-mode shortcut for http://10.0.0.201:8504.
# The icon is logo.ico inside the Desktop folder "Project Sage LAN".
# The shortcut stores that icon path with %USERPROFILE%, so copying the
# folder onto another Windows Desktop keeps the Sage icon.
#
#   powershell -ExecutionPolicy Bypass -File scripts\install_lan_edge_shortcut.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SourceIcon = Join-Path $ProjectRoot "assets\logo.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$PackName = "Project Sage LAN"
$PackDir = Join-Path $Desktop $PackName
$IconName = "logo.ico"
$IconPath = Join-Path $PackDir $IconName
$LnkName = "Project Sage.lnk"
$PackLnk = Join-Path $PackDir $LnkName
$DesktopLnk = Join-Path $Desktop "$PackName.lnk"
$Url = "http://10.0.0.201:8504"
$EdgeEnv = "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
$IconEnv = "%USERPROFILE%\Desktop\$PackName\$IconName"

if (-not (Test-Path -LiteralPath $SourceIcon)) {
    Write-Error "Icon not found: $SourceIcon"
}

$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edge)) {
    $edge = Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"
}
if (-not (Test-Path -LiteralPath $edge)) {
    Write-Error "Microsoft Edge was not found."
}

New-Item -ItemType Directory -Force -Path $PackDir | Out-Null
Copy-Item -LiteralPath $SourceIcon -Destination $IconPath -Force

$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($PackLnk)
$sc.TargetPath = $edge
$sc.Arguments = "--app=$Url"
$sc.WorkingDirectory = $PackDir
$sc.WindowStyle = 1
$sc.Description = "Project Sage - Edge app at $Url"
$sc.IconLocation = "$IconPath,0"
$sc.Save()

function New-EnvBlock {
    param(
        [string]$SignatureHex,
        [string]$Text
    )
    $signature = [Convert]::ToUInt32($SignatureHex, 16)
    $block = New-Object byte[] 0x314
    [BitConverter]::GetBytes([uint32]0x314).CopyTo($block, 0)
    [BitConverter]::GetBytes($signature).CopyTo($block, 4)
    $ansi = [System.Text.Encoding]::ASCII.GetBytes($Text)
    $uni = [System.Text.Encoding]::Unicode.GetBytes($Text)
    if ($ansi.Length -ge 259 -or $uni.Length -ge 518) {
        throw "Environment path is too long: $Text"
    }
    [Array]::Copy($ansi, 0, $block, 8, $ansi.Length)
    [Array]::Copy($uni, 0, $block, 268, $uni.Length)
    return $block
}

function Add-LnkEnvironmentBlocks {
    param(
        [string]$LnkPath,
        [string]$TargetEnv,
        [string]$IconEnvPath
    )
    $bytes = [System.IO.File]::ReadAllBytes($LnkPath)
    if ($bytes.Length -lt 8) { throw "Shortcut is too small: $LnkPath" }
    $term = [BitConverter]::ToUInt32($bytes, $bytes.Length - 4)
    if ($term -ne 0) { throw "Shortcut does not end with a terminal block: $LnkPath" }

    $targetBlock = New-EnvBlock -SignatureHex "A0000001" -Text $TargetEnv
    $iconBlock = New-EnvBlock -SignatureHex "A0000007" -Text $IconEnvPath
    $insertLen = $targetBlock.Length + $iconBlock.Length
    $out = New-Object byte[] ($bytes.Length + $insertLen)
    [Array]::Copy($bytes, 0, $out, 0, $bytes.Length - 4)
    [Array]::Copy($targetBlock, 0, $out, $bytes.Length - 4, $targetBlock.Length)
    [Array]::Copy($iconBlock, 0, $out, $bytes.Length - 4 + $targetBlock.Length, $iconBlock.Length)
    [System.IO.File]::WriteAllBytes($LnkPath, $out)
}

Add-LnkEnvironmentBlocks -LnkPath $PackLnk -TargetEnv $EdgeEnv -IconEnvPath $IconEnv
Copy-Item -LiteralPath $PackLnk -Destination $DesktopLnk -Force

$iniPath = Join-Path $PackDir "desktop.ini"
if (Test-Path -LiteralPath $iniPath) {
    attrib.exe -h -s $iniPath | Out-Null
}
$ini = @"
[.ShellClassInfo]
IconResource=logo.ico,0
InfoTip=Project Sage at $Url
"@
Set-Content -LiteralPath $iniPath -Value $ini -Encoding ASCII
attrib.exe +s $PackDir | Out-Null
attrib.exe +h +s $iniPath | Out-Null

$check = $shell.CreateShortcut($PackLnk)
$stored = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($PackLnk))
Write-Host "Folder: $PackDir"
Write-Host "Desktop shortcut: $DesktopLnk"
Write-Host "Target: $($check.TargetPath)"
Write-Host "Arguments: $($check.Arguments)"
Write-Host "Icon: $($check.IconLocation)"
if ($check.TargetPath -notmatch "msedge.exe") { Write-Error "Shortcut target is not Edge." }
if ($check.Arguments -notmatch [regex]::Escape($Url)) { Write-Error "Shortcut URL is wrong." }
if ($stored.IndexOf($IconEnv) -lt 0) { Write-Error "Icon environment path was not stored in the shortcut." }
if ($stored.IndexOf($EdgeEnv) -lt 0) { Write-Error "Edge environment path was not stored in the shortcut." }
Write-Host "Portable icon path stored: $IconEnv"

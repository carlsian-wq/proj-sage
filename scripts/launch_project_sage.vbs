' Silent-ish launcher for Project Sage desktop shortcut.
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fso.GetParentFolderName(scriptDir)
ps1 = scriptDir & "\launch_project_sage.ps1"
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """"
shell.CurrentDirectory = projectRoot
shell.Run cmd, 1, False

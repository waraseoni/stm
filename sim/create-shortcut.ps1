# Create a desktop shortcut for the stmlab GUI (run once per PC).
# Usage: powershell -ExecutionPolicy Bypass -File sim\create-shortcut.ps1

$desktop = [Environment]::GetFolderPath('Desktop')
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$desktop\stmlab GUI.lnk")
$sc.TargetPath = "pythonw.exe"
$sc.Arguments = "-m stmlab.gui"
$sc.WorkingDirectory = $PSScriptRoot
$sc.IconLocation = "pythonw.exe,0"
$sc.Description = "stmlab - STM32 simulator and IC read/write"
$sc.Save()
Write-Host "Shortcut created: $desktop\stmlab GUI.lnk" -ForegroundColor Green
# Script to exclude .venv from Google Drive sync
# This script adds the .venv folder to Google Drive's excluded folders list

$projectPath = "G:\Meu Drive\dev\CartoriosBR"
$venvPath = Join-Path $projectPath ".venv"

Write-Host "Excluding .venv from Google Drive sync..." -ForegroundColor Cyan
Write-Host "Path: $venvPath" -ForegroundColor Yellow

# Method 1: Using Google Drive's desktop app settings
# The user needs to manually exclude the folder via Google Drive settings
# This script will create a marker file to help identify the folder

$markerFile = Join-Path $venvPath "DO_NOT_SYNC.txt"
$markerContent = @"
This folder (.venv) should NOT be synced with Google Drive.

To exclude this folder from sync:
1. Right-click on the Google Drive icon in the system tray
2. Click on the gear icon (Settings)
3. Go to 'Preferences' > 'Google Drive' > 'Folder'
4. Click 'Add folder' under 'Folders from your computer'
5. Navigate to: $projectPath
6. Uncheck the '.venv' folder
7. Click 'Done'

Alternatively, you can exclude it by:
1. Right-clicking on the .venv folder in File Explorer
2. Selecting 'Offline access' > 'Remove offline access'
3. Then right-click again and select 'Make available offline' > 'Never'

This folder contains Python virtual environment files that are machine-specific
and should be recreated on each device rather than synced.
"@

if (Test-Path $venvPath) {
    Set-Content -Path $markerFile -Value $markerContent -Force
    Write-Host "`n✓ Created marker file: $markerFile" -ForegroundColor Green
    Write-Host "`nIMPORTANT: Please follow the instructions in the marker file to complete the exclusion." -ForegroundColor Yellow
    Write-Host "Opening the marker file now..." -ForegroundColor Cyan
    Start-Process notepad.exe -ArgumentList $markerFile
} else {
    Write-Host "`n✗ .venv folder not found at: $venvPath" -ForegroundColor Red
}

Write-Host "`nNote: Google Drive for Desktop doesn't provide a command-line interface" -ForegroundColor Gray
Write-Host "for managing sync exclusions. Manual configuration is required." -ForegroundColor Gray

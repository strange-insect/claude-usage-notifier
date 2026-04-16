# Build Claude Usage Notifier and register it to run at Windows startup.
param(
    [switch]$Unregister
)

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExePath     = Join-Path $ScriptDir "dist\claude_usage_notifier.exe"
$StartupDir  = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "ClaudeUsageNotifier.lnk"

if ($Unregister) {
    if (Test-Path $ShortcutPath) {
        Remove-Item $ShortcutPath -Force
        Write-Host "Unregistered from startup."
    } else {
        Write-Host "Not registered."
    }
    exit 0
}

# Prepare venv
$VenvDir    = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating venv: $VenvDir"
    python -m venv $VenvDir
}

# Build with PyInstaller
Write-Host "Building with PyInstaller..."
& $VenvPython -m pip install --quiet -r (Join-Path $ScriptDir "requirements.txt")
& $VenvPython -m pip install --quiet pyinstaller
& $VenvPython -m PyInstaller --noconfirm --onefile --windowed `
    --name claude_usage_notifier `
    --paths (Join-Path $ScriptDir "src") `
    (Join-Path $ScriptDir "src\claude_usage_notifier.py")
if (-not (Test-Path $ExePath)) {
    Write-Error "Build failed. dist\claude_usage_notifier.exe not found."
    exit 1
}
Write-Host "Build complete: $ExePath"

# Create shortcut in Startup folder
$WshShell  = New-Object -ComObject WScript.Shell
$Shortcut  = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath     = $ExePath
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.WindowStyle    = 1
$Shortcut.Save()

Write-Host "Registered to startup: $ShortcutPath"

# Stop any existing process, then launch
Get-Process -Name "claude_usage_notifier" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Process -FilePath $ExePath -WorkingDirectory $ScriptDir
Write-Host "Launched: $ExePath"
Write-Host "It will also auto-start on next login."

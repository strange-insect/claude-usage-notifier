# Update Claude Usage Notifier.
# Rebuilds the exe and re-registers startup by default.
param(
    [switch]$Dev,   # Only update venv (skip exe build / startup registration)
    [switch]$Local  # Skip git pull (install from local working tree as-is)
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-AppVersion {
    $initFile = Join-Path $ScriptDir "src\notifier\__init__.py"
    if (Test-Path $initFile) {
        $match = Select-String -Path $initFile -Pattern '__version__\s*=\s*"([^"]+)"'
        if ($match) { return $match.Matches.Groups[1].Value }
    }
    return $null
}

Push-Location $ScriptDir
try {
    $versionBefore = Get-AppVersion

    # Stop running process
    $proc = Get-Process -Name "claude_usage_notifier" -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Stopping running process..."
        $proc | Stop-Process -Force
        Start-Sleep -Seconds 1
    }

    if (-not $Local) {
        Write-Host "Pulling latest source..."
        git pull
        if ($LASTEXITCODE -ne 0) { throw "git pull failed." }
    } else {
        Write-Host "Skipping git pull (local mode)."
    }

    if ($Dev) {
        # Dev mode: just update venv
        $VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
        if (-not (Test-Path $VenvPython)) {
            Write-Host "Creating venv..."
            python -m venv (Join-Path $ScriptDir ".venv")
        }
        Write-Host "Updating dependencies..."
        & $VenvPython -m pip install --quiet -r requirements.txt
        Write-Host "Done. Start the app manually:"
        Write-Host "  python src\claude_usage_notifier.py"
    } else {
        # Rebuild & re-register
        Write-Host "Rebuilding and registering..."
        & (Join-Path $ScriptDir "register_startup.ps1")
    }

    $versionAfter = Get-AppVersion
    if ($versionBefore -and $versionAfter -and $versionBefore -ne $versionAfter) {
        Write-Host "Updated: v$versionBefore -> v$versionAfter"
    } elseif ($versionAfter) {
        Write-Host "Version: v$versionAfter"
    }
    Write-Host "Update complete."
} finally {
    Pop-Location
}

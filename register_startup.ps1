# Claude Usage Notifier をビルドしてスタートアップに登録する
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
        Write-Host "スタートアップ登録を解除しました。"
    } else {
        Write-Host "登録されていません。"
    }
    exit 0
}

# venv を用意
$VenvDir    = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "venv を作成します: $VenvDir"
    python -m venv $VenvDir
}

# PyInstaller でビルド
if (-not (Test-Path $ExePath)) {
    Write-Host "exe が見つかりません。PyInstaller でビルドします..."
    & $VenvPython -m pip install --quiet -r (Join-Path $ScriptDir "requirements.txt")
    & $VenvPython -m pip install --quiet pyinstaller
    & $VenvPython -m PyInstaller --noconfirm --onefile --windowed `
        --name claude_usage_notifier `
        --paths (Join-Path $ScriptDir "src") `
        (Join-Path $ScriptDir "src\claude_usage_notifier.py")
    if (-not (Test-Path $ExePath)) {
        Write-Error "ビルド失敗。dist\claude_usage_notifier.exe が見つかりません。"
        exit 1
    }
    Write-Host "ビルド完了: $ExePath"
} else {
    Write-Host "既存の exe を使用します: $ExePath"
}

# スタートアップにショートカット作成
$WshShell  = New-Object -ComObject WScript.Shell
$Shortcut  = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath     = $ExePath
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.WindowStyle    = 1
$Shortcut.Save()

Write-Host "スタートアップに登録しました: $ShortcutPath"
Write-Host "次回ログイン時から自動起動します。今すぐ起動する場合は Start-Process '$ExePath'"

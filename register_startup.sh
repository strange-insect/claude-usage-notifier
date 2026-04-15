#!/bin/bash
# Claude Usage Notifier を launchd のユーザーエージェントとして登録する (macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.claude-usage-notifier"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
APP_SUPPORT_DIR="$HOME/Library/Application Support/ClaudeUsageNotifier"

if [[ "${1:-}" == "-u" || "${1:-}" == "--unregister" ]]; then
    launchctl bootout "gui/$(id -u)/$PLIST_LABEL" 2>/dev/null || launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "スタートアップ登録を解除しました: $PLIST_PATH"
    exit 0
fi

VENV="$SCRIPT_DIR/.venv"
VENV_PY="$VENV/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
    echo "venv を作成します: $VENV"
    python3 -m venv "$VENV"
    "$VENV_PY" -m pip install --quiet --upgrade pip
    "$VENV_PY" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi

ENTRY="$SCRIPT_DIR/src/claude_usage_notifier.py"

mkdir -p "$APP_SUPPORT_DIR"
mkdir -p "$(dirname "$PLIST_PATH")"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PY</string>
        <string>$ENTRY</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>StandardOutPath</key>
    <string>$APP_SUPPORT_DIR/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>$APP_SUPPORT_DIR/launchd.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$PLIST_LABEL" 2>/dev/null || launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/$PLIST_LABEL"

echo "スタートアップに登録しました: $PLIST_PATH"
echo "次回ログイン時から自動起動します。すぐに確認したい場合はトレイアイコンを確認してください。"
echo "解除は: $0 --unregister"

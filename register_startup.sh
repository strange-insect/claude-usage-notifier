#!/bin/bash
# Register Claude Usage Notifier as a launchd user agent (macOS).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.claude-usage-notifier"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
APP_SUPPORT_DIR="$HOME/Library/Application Support/ClaudeUsageNotifier"

if [[ "${1:-}" == "-u" || "${1:-}" == "--unregister" ]]; then
    launchctl bootout "gui/$(id -u)/$PLIST_LABEL" 2>/dev/null || launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "Unregistered from startup: $PLIST_PATH"
    exit 0
fi

VENV="$SCRIPT_DIR/.venv"
VENV_PY="$VENV/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
    echo "Creating venv: $VENV"
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

echo "Registered to startup: $PLIST_PATH"
echo "Launched now; will also auto-start on next login. Check the tray icon."
echo "To unregister: $0 --unregister"

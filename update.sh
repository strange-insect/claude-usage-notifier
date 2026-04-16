#!/bin/bash
# Update Claude Usage Notifier.
# Updates dependencies and re-registers startup by default.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

get_app_version() {
    local init_file="$SCRIPT_DIR/src/notifier/__init__.py"
    if [[ -f "$init_file" ]]; then
        sed -n 's/^__version__\s*=\s*"\([^"]*\)"/\1/p' "$init_file"
    fi
}

DEV=false
LOCAL=false
for arg in "$@"; do
    case "$arg" in
        --dev|-d)   DEV=true ;;
        --local|-l) LOCAL=true ;;
    esac
done

VERSION_BEFORE=$(get_app_version)

if $LOCAL; then
    echo "Skipping git pull (local mode)."
else
    echo "Pulling latest source..."
    git pull
fi

VENV_PY="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
    echo "Creating venv..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

echo "Updating dependencies..."
"$VENV_PY" -m pip install --quiet -r requirements.txt

if $DEV; then
    echo "Done. Start the app manually:"
    echo "  python src/claude_usage_notifier.py"
else
    # Re-register (restarts the agent automatically)
    echo "Re-registering startup..."
    "$SCRIPT_DIR/register_startup.sh"
fi

VERSION_AFTER=$(get_app_version)
if [[ -n "$VERSION_BEFORE" && -n "$VERSION_AFTER" && "$VERSION_BEFORE" != "$VERSION_AFTER" ]]; then
    echo "Updated: v$VERSION_BEFORE -> v$VERSION_AFTER"
elif [[ -n "$VERSION_AFTER" ]]; then
    echo "Version: v$VERSION_AFTER"
fi
echo "Update complete."

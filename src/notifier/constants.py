import os
from pathlib import Path

from .platform_integration import config_dir

APP_NAME = "Claude Usage Notifier"

CONFIG_DIR = config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"
LOG_PATH = CONFIG_DIR / "app.log"

OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_USAGE_INTERVAL = 60

CREDENTIALS_PATHS = [
    Path(os.environ.get("APPDATA", "")) / "Claude" / ".credentials.json",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Claude" / ".credentials.json",
    Path.home() / ".claude" / ".credentials.json",
    Path.home() / ".config" / "claude" / ".credentials.json",
    Path.home() / "Library" / "Application Support" / "Claude" / ".credentials.json",
]

PLAN_KEYS = [
    ("five_hour", "5時間枠"),
    ("seven_day", "7日間"),
]
OVERRUN_REPEAT_SECONDS = 300

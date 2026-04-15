import json
import threading
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from .constants import CREDENTIALS_PATHS, OAUTH_USAGE_INTERVAL, OAUTH_USAGE_URL
from .utils import safe_float


def load_oauth_token() -> str:
    for path in CREDENTIALS_PATHS:
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                token = data.get("claudeAiOauth", {}).get("accessToken", "")
                if token:
                    return token
        except Exception:
            continue
    return ""


@dataclass
class PlanUsage:
    five_hour: float = -1.0
    five_hour_resets_at: str = ""
    seven_day: float = -1.0
    seven_day_resets_at: str = ""
    last_updated: float = 0.0
    error: str = ""

    def resets_at_local(self, iso: str) -> str:
        if not iso:
            return ""
        try:
            dt = datetime.fromisoformat(iso)
            return dt.astimezone().strftime("%m/%d %H:%M")
        except Exception:
            return iso


@dataclass
class PlanAlertState:
    crossed_80: bool = False
    crossed_90: bool = False
    crossed_100: bool = False
    silenced_until_reset: bool = False
    last_overrun_notify_ts: float = 0.0
    last_resets_at: str = ""


class PlanUsagePoller(threading.Thread):
    def __init__(self, on_update):
        super().__init__(daemon=True)
        self.on_update = on_update
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.wait(OAUTH_USAGE_INTERVAL):
            self._poll()

    def poll_now(self):
        threading.Thread(target=self._poll, daemon=True).start()

    def _poll(self):
        usage = PlanUsage(last_updated=time.time())
        token = load_oauth_token()
        if not token:
            usage.error = "credentials not found"
            self.on_update(usage)
            return
        try:
            req = urllib.request.Request(
                OAUTH_USAGE_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "anthropic-beta": "oauth-2025-04-20",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            def pct(key):
                v = data.get(key)
                if v is None:
                    return -1.0
                return safe_float(v.get("utilization"), -1.0)

            def resets(key):
                v = data.get(key)
                if v is None:
                    return ""
                return str(v.get("resets_at") or "")

            usage.five_hour = pct("five_hour")
            usage.five_hour_resets_at = resets("five_hour")
            usage.seven_day = pct("seven_day")
            usage.seven_day_resets_at = resets("seven_day")
        except Exception as e:
            usage.error = str(e)
        self.on_update(usage)

    def stop(self):
        self._stop_event.set()

import json

from .constants import CONFIG_DIR, CONFIG_PATH


class AppConfig:
    def __init__(self):
        self.periodic_notification_minutes = 30  # 0=off, 30, 60
        self.language = "auto"  # auto, en, ja
        self.load()

    def load(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            self.save()
            return
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        raw = int(data.get("periodic_notification_minutes", self.periodic_notification_minutes))
        self.periodic_notification_minutes = raw if raw in (0, 30, 60) else 30
        lang = str(data.get("language", self.language))
        self.language = lang if lang in ("auto", "en", "ja") else "auto"

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "periodic_notification_minutes": self.periodic_notification_minutes,
            "language": self.language,
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

from .platform_integration import build_notification_backends


class NotificationManager:
    def __init__(self, icon_path=None, app_id: str = "Claude Usage Alert"):
        self.icon_path = str(icon_path) if icon_path else None
        self.app_id = app_id
        self._backends = build_notification_backends()

    def notify(self, title: str, body: str, buttons=None, on_click=None, silent: bool = False):
        for backend in self._backends:
            try:
                backend.send(
                    title=title,
                    body=body,
                    icon_path=self.icon_path,
                    silent=silent,
                    buttons=buttons,
                    on_click=on_click,
                    app_id=self.app_id,
                )
                return
            except Exception:
                continue
        print(f"[NOTIFY] {title}: {body}")

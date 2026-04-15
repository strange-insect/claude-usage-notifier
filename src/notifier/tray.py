import pystray
from PIL import Image, ImageDraw

from .constants import PLAN_KEYS

CLAUDE_CORAL = (217, 119, 87, 255)
TRACK_COLOR = (55, 55, 65, 255)


def _progress_color(pct: float):
    if pct >= 100:
        return (220, 70, 70, 255)
    if pct >= 90:
        return (240, 150, 50, 255)
    if pct >= 80:
        return (240, 200, 60, 255)
    return (90, 185, 140, 255)


def make_tray_image(usage_pct: float = -1.0) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    ring_box = (3, 3, size - 3, size - 3)
    d.arc(ring_box, start=0, end=360, fill=TRACK_COLOR, width=6)

    if usage_pct >= 0:
        angle = min(360.0, usage_pct * 3.6)
        d.arc(ring_box, start=-90, end=-90 + angle, fill=_progress_color(usage_pct), width=6)

    d.ellipse((18, 18, size - 18, size - 18), fill=CLAUDE_CORAL)
    return img


def _periodic_menu(app) -> pystray.Menu:
    def make(minutes: int, text: str):
        return pystray.MenuItem(
            text,
            lambda _i, _it: app.set_periodic_interval(minutes),
            checked=lambda _it, m=minutes: app.config.periodic_notification_minutes == m,
            radio=True,
        )
    return pystray.Menu(
        make(0, "オフ"),
        make(30, "30分ごと"),
        make(60, "1時間ごと"),
    )


def _mute_menu(app) -> pystray.Menu:
    def make(key: str, label: str):
        def action(_icon, _item):
            app.toggle_plan_mute(key, label)
        def checked(_item):
            return app.is_plan_muted(key)
        return pystray.MenuItem(label, action, checked=checked)
    return pystray.Menu(*[make(k, l) for k, l in PLAN_KEYS])


def build_icon(app) -> pystray.Icon:
    from .constants import APP_NAME

    menu = pystray.Menu(
        pystray.MenuItem(app.menu_plan_label("five_hour", "5h"), None, enabled=False),
        pystray.MenuItem(app.menu_plan_label("seven_day", "7d"), None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("今すぐ更新", app.refresh_plan_now),
        pystray.MenuItem("現在の使用量を通知", app.show_current_usage),
        pystray.MenuItem("定期通知", _periodic_menu(app)),
        pystray.MenuItem("次のリセットまでミュート", _mute_menu(app)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("設定ファイルを開く", app.open_config),
        pystray.MenuItem("ログを開く", app.open_log),
        pystray.MenuItem("使用率CSVを保存...", app.save_usage_csv),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("終了", app.quit),
    )
    return pystray.Icon(
        "claude_usage_notifier",
        icon=make_tray_image(),
        title=APP_NAME,
        menu=menu,
    )

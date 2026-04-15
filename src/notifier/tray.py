import pystray
from PIL import Image, ImageDraw

from .constants import PLAN_KEYS
from .i18n import t

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
    def make(minutes: int, key: str):
        return pystray.MenuItem(
            lambda _it: t(key),
            lambda _i, _it: app.set_periodic_interval(minutes),
            checked=lambda _it, m=minutes: app.config.periodic_notification_minutes == m,
            radio=True,
        )
    return pystray.Menu(
        make(0, "periodic.off"),
        make(30, "periodic.30min"),
        make(60, "periodic.60min"),
    )


def _mute_menu(app) -> pystray.Menu:
    def make(key: str):
        def action(_icon, _item):
            app.toggle_plan_mute(key, t(f"plan.{key}"))
        def checked(_item):
            return app.is_plan_muted(key)
        return pystray.MenuItem(lambda _it, k=key: t(f"plan.{k}"), action, checked=checked)
    return pystray.Menu(*[make(k) for k in PLAN_KEYS])


def _language_menu(app) -> pystray.Menu:
    def make(code: str, label):
        return pystray.MenuItem(
            label,
            lambda _i, _it: app.set_language(code),
            checked=lambda _it, c=code: app.config.language == c,
            radio=True,
        )
    return pystray.Menu(
        make("auto", lambda _it: t("menu.lang_auto")),
        make("en", "English"),
        make("ja", "日本語"),
    )


def build_icon(app) -> pystray.Icon:
    from .constants import APP_NAME

    menu = pystray.Menu(
        pystray.MenuItem(app.menu_plan_label("five_hour", "5h"), None, enabled=False),
        pystray.MenuItem(app.menu_plan_label("seven_day", "7d"), None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda _it: t("menu.refresh_now"), app.refresh_plan_now),
        pystray.MenuItem(lambda _it: t("menu.notify_current"), app.show_current_usage),
        pystray.MenuItem(lambda _it: t("menu.periodic"), _periodic_menu(app)),
        pystray.MenuItem(lambda _it: t("menu.mute_until_reset"), _mute_menu(app)),
        pystray.MenuItem(lambda _it: t("menu.language"), _language_menu(app)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda _it: t("menu.open_config"), app.open_config),
        pystray.MenuItem(lambda _it: t("menu.open_log"), app.open_log),
        pystray.MenuItem(lambda _it: t("menu.save_csv"), app.save_usage_csv),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda _it: t("menu.quit"), app.quit),
    )
    return pystray.Icon(
        "claude_usage_notifier",
        icon=make_tray_image(),
        title=APP_NAME,
        menu=menu,
    )

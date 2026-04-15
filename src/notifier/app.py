import sys
import threading
import time
from datetime import datetime, timedelta

from .config import AppConfig
from .constants import (
    APP_NAME,
    CONFIG_DIR,
    CONFIG_PATH,
    LOG_PATH,
    OVERRUN_REPEAT_SECONDS,
    PLAN_KEYS,
)
from .i18n import set_language, t
from .notifications import NotificationManager
from .platform_integration import open_path
from .plan_usage import PlanAlertState, PlanUsage, PlanUsagePoller
from .tray import build_icon, make_tray_image
from .usage_log import USAGE_CSV_PATH, append_usage_row
from .utils import now_str


class ClaudeUsageNotifierApp:
    def __init__(self):
        self.config = AppConfig()
        set_language(self.config.language)
        self.icon_file = self._save_icon_file()
        self.notifications = NotificationManager(icon_path=self.icon_file)
        self.plan_usage = PlanUsage()
        self.plan_poller = None
        self.plan_alert_states = {key: PlanAlertState() for key in PLAN_KEYS}
        self._stop_event = threading.Event()
        self.icon = None

    @staticmethod
    def _save_icon_file():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        path = CONFIG_DIR / "app_icon.png"
        try:
            make_tray_image().save(path)
        except Exception:
            return None
        return path

    # ---- logging ----

    def log(self, message: str):
        line = f"[{now_str()}] {message}\n"
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    # ---- lifecycle ----

    def _start_plan_poller(self):
        self.plan_poller = PlanUsagePoller(on_update=self._on_plan_usage)
        self.plan_poller.start()
        self.plan_poller.poll_now()

    def run(self):
        self.log(t("log.app_started"))
        self._start_plan_poller()
        threading.Thread(target=self._hourly_scheduler, daemon=True).start()
        self.icon = build_icon(self)
        self.icon.run()

    # ---- plan usage handling ----

    def _on_plan_usage(self, usage: PlanUsage):
        self.plan_usage = usage
        try:
            append_usage_row(usage)
        except Exception as e:
            self.log(t("log.csv_write_failed", err=e))
        self._check_plan_alerts(usage)
        if self.icon is not None:
            try:
                self.icon.update_menu()
                self.icon.title = self._tooltip()
                self.icon.icon = make_tray_image(self._max_plan_pct())
            except Exception:
                pass

    def _max_plan_pct(self) -> float:
        vals = [getattr(self.plan_usage, k) for k in PLAN_KEYS]
        vals = [v for v in vals if v >= 0]
        return max(vals) if vals else -1.0

    def _tooltip(self) -> str:
        u = self.plan_usage
        if u.error:
            return f"{APP_NAME}\n" + t("tooltip.error", error=u.error)

        def fmt(v):
            return f"{v:.0f}%" if v >= 0 else "-"

        return (
            f"{APP_NAME}\n"
            f"5h: {fmt(u.five_hour)}  "
            f"7d: {fmt(u.seven_day)}"
        )

    def _check_plan_alerts(self, u: PlanUsage):
        now = time.time()
        for key in PLAN_KEYS:
            label = t(f"plan.{key}")
            val = getattr(u, key)
            if val < 0:
                continue
            resets_at = getattr(u, f"{key}_resets_at", "")
            state = self.plan_alert_states[key]

            if resets_at and resets_at != state.last_resets_at:
                if state.last_resets_at:
                    self.log(t("log.usage_reset", label=label))
                state.crossed_80 = False
                state.crossed_90 = False
                state.crossed_100 = False
                state.silenced_until_reset = False
                state.last_overrun_notify_ts = 0.0
                state.last_resets_at = resets_at

            if state.silenced_until_reset:
                continue

            if val >= 80 and not state.crossed_80:
                state.crossed_80 = True
                self._notify_plan_threshold(u, key, label, val, 80)
            if val >= 90 and not state.crossed_90:
                state.crossed_90 = True
                self._notify_plan_threshold(u, key, label, val, 90)
            if val >= 100:
                if not state.crossed_100:
                    state.crossed_100 = True
                    state.last_overrun_notify_ts = now
                    self._notify_plan_overrun(u, key, label, val)
                elif now - state.last_overrun_notify_ts >= OVERRUN_REPEAT_SECONDS:
                    state.last_overrun_notify_ts = now
                    self._notify_plan_overrun(u, key, label, val)

    def _reset_line(self, u: PlanUsage, key: str) -> str:
        iso = getattr(u, f"{key}_resets_at", "")
        local = u.resets_at_local(iso)
        return t("notify.reset", local=local) if local else ""

    def _notify_plan_threshold(self, u: PlanUsage, key: str, label: str, val: float, level: int):
        title = t("notify.threshold_title", label=label, level=level)
        body = t("notify.current", val=val)
        reset = self._reset_line(u, key)
        if reset:
            body += f"  |  {reset}"
        self.notifications.notify(title, body)
        self.log(t("log.alert", title=title, body=body))

    def _notify_plan_overrun(self, u: PlanUsage, key: str, label: str, val: float):
        title = t("notify.overrun_title", label=label)
        body = t("notify.current_over", val=val)
        reset = self._reset_line(u, key)
        if reset:
            body += f"  |  {reset}"
        self.notifications.notify(title, body)
        self.log(t("log.alert", title=title, body=body))

    # ---- periodic ----

    def _hourly_scheduler(self):
        while not self._stop_event.is_set():
            interval = self.config.periodic_notification_minutes
            if interval == 0:
                if self._stop_event.wait(60):
                    return
                continue
            now = datetime.now()
            if interval == 30:
                if now.minute < 30:
                    target = now.replace(minute=30, second=0, microsecond=0)
                else:
                    target = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            else:
                target = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            delay = max(1.0, (target - now).total_seconds())
            if self._stop_event.wait(delay):
                return
            if self.config.periodic_notification_minutes != 0:
                self._send_periodic_notification()

    def _send_periodic_notification(self):
        u = self.plan_usage
        if u.error:
            return

        def fmt(v):
            return f"{v:.0f}%" if v >= 0 else "-"

        title = t("notify.periodic_title")
        body = t("notify.body", five=fmt(u.five_hour), seven=fmt(u.seven_day))
        muted = [t(f"plan.{k}") for k in PLAN_KEYS if self.plan_alert_states[k].silenced_until_reset]
        if muted:
            body += "\n" + t("notify.muted_list", labels=", ".join(muted))
        self.notifications.notify(title, body, silent=True)
        self.log(t("log.periodic", body=body))

    # ---- tray callbacks ----

    def menu_plan_label(self, key: str, display: str):
        def label(_):
            val = getattr(self.plan_usage, key)
            pct = f"{val:.0f}%" if val >= 0 else "-"
            return f"{display}: {pct}"
        return label

    def show_current_usage(self, icon, item):
        u = self.plan_usage

        def fmt(v):
            return f"{v:.0f}%" if v >= 0 else "-"

        title = t("notify.current_title")
        body = t("notify.body", five=fmt(u.five_hour), seven=fmt(u.seven_day))
        self.notifications.notify(title, body, silent=True)

    def refresh_plan_now(self, icon, item):
        if self.plan_poller:
            self.plan_poller.poll_now()

    def set_periodic_interval(self, minutes: int):
        self.config.periodic_notification_minutes = minutes
        try:
            self.config.save()
        except Exception as e:
            self.log(t("log.config_save_failed", err=e))
        label_map = {0: "periodic.off", 30: "periodic.30min", 60: "periodic.60min"}
        label = t(label_map[minutes]) if minutes in label_map else str(minutes)
        self.log(t("log.periodic_changed", label=label))
        if self.icon is not None:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def set_language(self, lang: str):
        if lang not in ("auto", "en", "ja") or lang == self.config.language:
            return
        self.config.language = lang
        try:
            self.config.save()
        except Exception as e:
            self.log(t("log.config_save_failed", err=e))
        set_language(lang)
        label = {"auto": t("menu.lang_auto"), "en": "English", "ja": "日本語"}[lang]
        self.log(t("log.language_changed", label=label))
        if self.icon is not None:
            try:
                self.icon.update_menu()
                self.icon.title = self._tooltip()
            except Exception:
                pass

    def is_plan_muted(self, key: str) -> bool:
        state = self.plan_alert_states.get(key)
        return bool(state and state.silenced_until_reset)

    def toggle_plan_mute(self, key: str, label: str):
        state = self.plan_alert_states.get(key)
        if not state:
            return
        state.silenced_until_reset = not state.silenced_until_reset
        self.log(t("log.mute_on" if state.silenced_until_reset else "log.mute_off", label=label))
        if self.icon is not None:
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def open_config(self, icon, item):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            self.config.save()
        open_path(CONFIG_PATH)

    def open_log(self, icon, item):
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_PATH.exists():
            LOG_PATH.write_text("", encoding="utf-8")
        open_path(LOG_PATH)

    def save_usage_csv(self, icon, item):
        threading.Thread(target=self._save_usage_csv_dialog, daemon=True).start()

    def _save_usage_csv_dialog(self):
        if not USAGE_CSV_PATH.exists():
            self.log(t("log.csv_not_yet"))
            return
        import shutil
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            default_name = t(
                "dialog.csv_default_name",
                date=datetime.now().strftime("%Y%m%d_%H%M"),
            )
            dest = filedialog.asksaveasfilename(
                parent=root,
                title=t("dialog.save_csv_title"),
                defaultextension=".csv",
                initialfile=default_name,
                filetypes=[
                    (t("dialog.csv_filetype"), "*.csv"),
                    (t("dialog.all_filetypes"), "*.*"),
                ],
            )
        finally:
            root.destroy()

        if not dest:
            return
        try:
            shutil.copy2(USAGE_CSV_PATH, dest)
            self.log(t("log.csv_saved", dest=dest))
        except Exception as e:
            self.log(t("log.csv_save_failed", err=e))

    def quit(self, icon, item):
        self._stop_event.set()
        if self.plan_poller is not None:
            self.plan_poller.stop()
        if self.icon is not None:
            self.icon.stop()


def main():
    if sys.platform not in ("win32", "darwin"):
        print(t("error.unsupported_platform"))
        return
    ClaudeUsageNotifierApp().run()

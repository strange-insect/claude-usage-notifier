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
from .notifications import NotificationManager
from .platform_integration import open_path
from .plan_usage import PlanAlertState, PlanUsage, PlanUsagePoller
from .tray import build_icon, make_tray_image
from .usage_log import USAGE_CSV_PATH, append_usage_row
from .utils import now_str


class ClaudeUsageNotifierApp:
    def __init__(self):
        self.config = AppConfig()
        self.icon_file = self._save_icon_file()
        self.notifications = NotificationManager(icon_path=self.icon_file)
        self.plan_usage = PlanUsage()
        self.plan_poller = None
        self.plan_alert_states = {key: PlanAlertState() for key, _ in PLAN_KEYS}
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
        self.log("アプリを起動しました。")
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
            self.log(f"CSV 書き込み失敗: {e}")
        self._check_plan_alerts(usage)
        if self.icon is not None:
            try:
                self.icon.update_menu()
                self.icon.title = self._tooltip()
                self.icon.icon = make_tray_image(self._max_plan_pct())
            except Exception:
                pass

    def _max_plan_pct(self) -> float:
        vals = [getattr(self.plan_usage, k) for k, _ in PLAN_KEYS]
        vals = [v for v in vals if v >= 0]
        return max(vals) if vals else -1.0

    def _tooltip(self) -> str:
        u = self.plan_usage
        if u.error:
            return f"{APP_NAME}\n取得失敗: {u.error}"

        def fmt(v):
            return f"{v:.0f}%" if v >= 0 else "-"

        return (
            f"{APP_NAME}\n"
            f"5h: {fmt(u.five_hour)}  "
            f"7d: {fmt(u.seven_day)}"
        )

    def _check_plan_alerts(self, u: PlanUsage):
        now = time.time()
        for key, label in PLAN_KEYS:
            val = getattr(u, key)
            if val < 0:
                continue
            resets_at = getattr(u, f"{key}_resets_at", "")
            state = self.plan_alert_states[key]

            if resets_at and resets_at != state.last_resets_at:
                if state.last_resets_at:
                    self.log(f"{label}: usage reset detected, clearing alert state")
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
        return f"リセット: {local}" if local else ""

    def _notify_plan_threshold(self, u: PlanUsage, key: str, label: str, val: float, level: int):
        title = f"⚠️ {label}の利用量が{level}%を超えました"
        body = f"現在 {val:.0f}%"
        reset = self._reset_line(u, key)
        if reset:
            body += f"  |  {reset}"
        self.notifications.notify(title, body)
        self.log(f"通知: {title} / {body}")

    def _notify_plan_overrun(self, u: PlanUsage, key: str, label: str, val: float):
        title = f"🚨 {label}の上限に到達しました"
        body = f"現在 {val:.0f}% (100%超過)"
        reset = self._reset_line(u, key)
        if reset:
            body += f"  |  {reset}"
        self.notifications.notify(title, body)
        self.log(f"通知: {title} / {body}")

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

        title = "📊 Claude 利用量 定期通知"
        body = f"5時間: {fmt(u.five_hour)}  |  7日間: {fmt(u.seven_day)}"
        muted = [label for (k, label) in PLAN_KEYS if self.plan_alert_states[k].silenced_until_reset]
        if muted:
            body += f"\nミュート中: {', '.join(muted)}"
        self.notifications.notify(title, body, silent=True)
        self.log(f"定期通知: {body}")

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

        title = "📊 Claude 現在の利用量"
        body = f"5時間: {fmt(u.five_hour)}  |  7日間: {fmt(u.seven_day)}"
        self.notifications.notify(title, body, silent=True)

    def refresh_plan_now(self, icon, item):
        if self.plan_poller:
            self.plan_poller.poll_now()

    def set_periodic_interval(self, minutes: int):
        self.config.periodic_notification_minutes = minutes
        try:
            self.config.save()
        except Exception as e:
            self.log(f"設定保存失敗: {e}")
        label = {0: "オフ", 30: "30分ごと", 60: "1時間ごと"}.get(minutes, str(minutes))
        self.log(f"定期通知を {label} に変更しました。")
        if self.icon is not None:
            try:
                self.icon.update_menu()
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
        self.log(f"{label}: {'リセットまで通知ミュート' if state.silenced_until_reset else 'ミュート解除'}")
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
            self.log("CSV 保存: usage.csv がまだ存在しません。")
            return
        import shutil
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            default_name = f"claude_usage_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            dest = filedialog.asksaveasfilename(
                parent=root,
                title="使用率CSVを保存",
                defaultextension=".csv",
                initialfile=default_name,
                filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            )
        finally:
            root.destroy()

        if not dest:
            return
        try:
            shutil.copy2(USAGE_CSV_PATH, dest)
            self.log(f"CSV を {dest} に保存しました。")
        except Exception as e:
            self.log(f"CSV 保存失敗: {e}")

    def quit(self, icon, item):
        self._stop_event.set()
        if self.plan_poller is not None:
            self.plan_poller.stop()
        if self.icon is not None:
            self.icon.stop()


def main():
    if sys.platform not in ("win32", "darwin"):
        print("Unsupported platform. Windows / macOS only.")
        return
    ClaudeUsageNotifierApp().run()

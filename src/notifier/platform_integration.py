"""OS 依存処理をここに集約。Windows / macOS の差分を吸収する。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


def config_dir() -> Path:
    if IS_WINDOWS:
        return Path(os.environ.get("APPDATA", Path.home())) / "ClaudeUsageNotifier"
    if IS_MACOS:
        return Path.home() / "Library" / "Application Support" / "ClaudeUsageNotifier"
    return Path.home() / ".config" / "ClaudeUsageNotifier"


def open_path(path: Path) -> None:
    """OS 標準のアプリでファイル/ディレクトリを開く。"""
    path = str(path)
    if IS_WINDOWS:
        try:
            os.startfile(path)  # noqa: S606
        except OSError:
            subprocess.Popen(["notepad.exe", path])
    elif IS_MACOS:
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


# ---------- notifications ----------

class _BaseBackend:
    def send(self, title, body, icon_path=None, silent=False, buttons=None, on_click=None, app_id=None):
        raise NotImplementedError


class _WindowsBackend(_BaseBackend):
    def __init__(self):
        try:
            from win11toast import toast  # type: ignore
        except Exception:
            self._toast = None
        else:
            self._toast = toast

    def send(self, title, body, icon_path=None, silent=False, buttons=None, on_click=None, app_id=None):
        if self._toast is None:
            raise RuntimeError("win11toast not available")
        kwargs = {"duration": "short"}
        if app_id:
            kwargs["app_id"] = app_id
        if icon_path:
            kwargs["icon"] = {"src": str(icon_path), "placement": "appLogoOverride"}
        if silent:
            kwargs["audio"] = {"silent": "true"}
        if buttons:
            kwargs["buttons"] = buttons
        if on_click:
            kwargs["on_click"] = on_click
        self._toast(title, body, **kwargs)


class _MacOSBackend(_BaseBackend):
    """macOS は osascript で表示する。buttons は未対応。silent は OS 設定依存。"""

    @staticmethod
    def _escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def send(self, title, body, icon_path=None, silent=False, buttons=None, on_click=None, app_id=None):
        title_s = self._escape(title)
        body_s = self._escape(body)
        subtitle = self._escape(app_id) if app_id else ""
        parts = [f'display notification "{body_s}" with title "{title_s}"']
        if subtitle:
            parts.append(f'subtitle "{subtitle}"')
        if not silent:
            parts.append('sound name "Glass"')
        script = " ".join(parts)
        subprocess.Popen(["osascript", "-e", script])


class _PowerShellFallbackBackend(_BaseBackend):
    def send(self, title, body, icon_path=None, silent=False, buttons=None, on_click=None, app_id=None):
        script = (
            "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
            f"[System.Windows.Forms.MessageBox]::Show("
            f"'{body.replace(chr(39), chr(39) * 2)}', "
            f"'{title.replace(chr(39), chr(39) * 2)}') | Out-Null"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def build_notification_backends():
    """優先順位つき backend リストを返す。最初に成功したものが使われる。"""
    if IS_WINDOWS:
        return [_WindowsBackend(), _PowerShellFallbackBackend()]
    if IS_MACOS:
        return [_MacOSBackend()]
    return []

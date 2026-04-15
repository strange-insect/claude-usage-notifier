# Claude Usage Notifier

[日本語版 README はこちら / Japanese README](README.ja.md)

A tray-resident app for Windows / macOS that monitors Claude Code Pro/Max plan usage and shows toast notifications.

- Polls remaining usage for the **5-hour window / 7-day window** every 60 seconds
- Tray icon shows a colored ring gauge that fills based on usage (status at a glance)
- Toast notifications at 80% / 90% / 100%; while over 100%, re-notifies every 5 minutes
- Periodic notifications (every 30 min / every hour / off) switchable from the tray menu
- Usage is appended to a CSV so you can graph it later
- **English / Japanese UI** — defaults to English, auto-detects Japanese system locale, or set explicitly in `config.json`

No window is opened. All interactions are via the tray icon's right-click menu.

## How it works

It reads the OAuth token Claude Code saves at login (`%APPDATA%\Claude\.credentials.json`, etc.) and calls Anthropic's internal endpoint `api.anthropic.com/api/oauth/usage` every 60 seconds to fetch usage. **No API key required** — if you are already logged into Claude Code with a subscription, no additional setup is needed.

## Prerequisites

- **Windows 10 / 11** or **macOS 12+**
- Python 3.11+
- Already logged into Claude Code with a **subscription (Pro/Max)**
- `python --version` works

### Platform differences

| Item | Windows | macOS |
|---|---|---|
| Notification backend | win11toast (toast) | `osascript` (Notification Center) |
| Silent notifications | Supported | Depends on system settings (must mute notification sound at the OS level) |
| Config directory | `%APPDATA%\ClaudeUsageNotifier\` | `~/Library/Application Support/ClaudeUsageNotifier/` |
| Credential search | `%APPDATA%\Claude\.credentials.json`, etc. | Also `~/Library/Application Support/Claude/.credentials.json`, `~/.claude/.credentials.json` |
| Startup autolaunch | `register_startup.ps1` (PyInstaller + Startup folder) | `register_startup.sh` (launchd LaunchAgent) |

## Setup

### Install

Uses a venv so the global environment stays clean.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS (bash/zsh):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` already branches OS-dependent packages (`win11toast` / `pyobjc`) via `sys_platform` markers.

### Run (for development / testing)

Windows:

```powershell
python src\claude_usage_notifier.py
```

macOS:

```bash
python src/claude_usage_notifier.py
```

An icon appears in the tray (menu bar) and the first poll runs after 60 seconds.

### Autolaunch at startup

**Windows:**

```powershell
.\register_startup.ps1
```

On first run it creates `.venv` at the project root, runs PyInstaller inside it to build `dist\claude_usage_notifier.exe`, and creates a shortcut in the Startup folder. It autolaunches from next login onward (since it's built as an exe, no venv or Python is needed at runtime). Remove with `-Unregister`.

**macOS:**

```bash
chmod +x register_startup.sh
./register_startup.sh
```

On first run it creates `.venv` with the dependencies, generates `~/Library/LaunchAgents/com.claude-usage-notifier.plist`, and registers it via `launchctl bootstrap`. It autolaunches from next login (and starts immediately as well).

Remove:

```bash
./register_startup.sh --unregister
```

launchd stdout / stderr go to `~/Library/Application Support/ClaudeUsageNotifier/launchd.{out,err}.log`.

## Notification rules

| Type | Timing | Sound |
|---|---|---|
| Threshold | Once each when **crossing** 80% / 90% / 100% | On |
| While over 100% | Re-notifies every 5 minutes | On |
| Periodic | Current usage at every :00 / :30 (default) | **Silent** |

- The 5-hour and 7-day windows are tracked independently. Either can be muted on its own
- Mute state auto-clears when the reset time (`resets_at` from the API) updates
- Toggle mute per window from the tray menu "Mute until next reset" (checked = muted)
- Periodic notification can be switched instantly via right-click menu "Periodic" → **Off / Every 30 min / Every hour** (saved to `config.json`)

> The notification's app name is shown as **Claude Usage Alert** (at the top of Windows Notification Center).

## Tray icon

At startup `app_icon.png` is generated in the config folder; the tray icon updates in real time.

### Gauge colors

The outer ring shows the **maximum** usage between the 5-hour and 7-day windows.

| State | Color |
|---|---|
| Under 80% | Teal (green) |
| 80% or higher | Yellow |
| 90% or higher | Orange |
| 100% or higher | Red |

The coral center is for app identification (Claude color).

### Right-click menu

- `5h: XX%` / `7d: XX%` (shows the latest values; not clickable)
- **Check now** — manually re-fetch usage
- **Notify current usage** — toast the current values (silent)
- **Periodic** — Off / Every 30 min / Every hour
- **Mute until next reset** — toggle per window (5-hour / 7-day); auto-unmutes at next reset
- **Open config file** / **Open log** — opens in Notepad, etc.
- **Save usage CSV...** — save-as dialog to copy anywhere
- **Quit**

## Saved files

Everything lives under the config directory (Windows: `%APPDATA%\ClaudeUsageNotifier\` / macOS: `~/Library/Application Support/ClaudeUsageNotifier/`):

| File | Content |
|---|---|
| `config.json` | Settings: periodic notification interval, UI language |
| `app.log` | Text log of startup / notifications / errors (append-only, no rotation) |
| `usage.csv` | Usage history per poll (see below) |
| `app_icon.png` | App icon used in toast notifications |

### usage.csv format

One row appended per successful poll. Columns:

| Column | Content |
|---|---|
| `timestamp` | Local time (ISO 8601, second precision) |
| `five_hour_pct` | 5-hour window usage (%) |
| `five_hour_resets_at` | 5-hour window reset time (UTC ISO) |
| `seven_day_pct` | 7-day window usage (%) |
| `seven_day_resets_at` | 7-day window reset time (UTC ISO) |

With 60-second polling that's about 1440 rows/day (~80 KB). Opens directly in Excel / pandas. If size becomes a concern, archive manually (no rotation).

## Language (UI)

The tray menu, notifications, and log messages are localized. `config.json`:

```json
{
  "periodic_notification_minutes": 30,
  "language": "auto"
}
```

| Value | Behavior |
|---|---|
| `"auto"` | Auto-detect from system locale (Japanese system → `ja`, otherwise `en`) |
| `"en"` | English (default) |
| `"ja"` | Japanese |

Edit and restart the app to apply. Add a new language by dropping a `STRINGS` dict in `src/notifier/locales/<code>.py` and registering it in `src/notifier/i18n.py`.

## Project structure

```
src/
  claude_usage_notifier.py      # entry point
  notifier/                     # package
    app.py                      # main app (resident loop, notification decisions)
    config.py                   # config load/save
    constants.py                # constants (plan definitions, etc.)
    i18n.py                     # translation lookup (t / set_language)
    locales/                    # translation resource files (en.py, ja.py)
    notifications.py            # notification manager (delegates to backend)
    platform_integration.py     # OS-dependent code (notification backend, paths, file open)
    plan_usage.py               # Usage API polling
    tray.py                     # pystray menu
    usage_log.py                # CSV logging
    utils.py                    # small helpers
register_startup.ps1            # Windows: PyInstaller build & Startup registration
register_startup.sh             # macOS: launchd LaunchAgent registration
requirements.txt                # branches OS-dependent packages via sys_platform
```

OS-dependent code is centralized in `platform_integration.py` on principle. Adding a new OS should only require adding a backend / path resolver there, without touching other modules.

## Caveats

- `api.anthropic.com/api/oauth/usage` is an **unofficial endpoint**. Anthropic may change or remove it in future updates
- The macOS version only has simple osascript-based notifications. Silent flag etc. depend on OS settings

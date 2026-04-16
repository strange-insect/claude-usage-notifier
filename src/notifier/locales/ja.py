# -*- coding: utf-8 -*-
STRINGS = {
    "plan.five_hour": "5時間枠",
    "plan.seven_day": "7日間",

    "menu.refresh_now": "今すぐチェック",
    "menu.notify_current": "現在の使用量を通知",
    "menu.periodic": "定期通知",
    "menu.mute_until_reset": "次のリセットまでミュート",
    "menu.language": "言語",
    "menu.lang_auto": "自動（システム）",
    "menu.open_config": "設定ファイルを開く",
    "menu.open_log": "ログを開く",
    "menu.save_csv": "使用率CSVを保存...",
    "menu.quit": "終了",

    "periodic.off": "オフ",
    "periodic.30min": "30分ごと",
    "periodic.60min": "1時間ごと",

    "notify.threshold_title": "\u26a0\ufe0f {label}の利用量が{level}%を超えました",
    "notify.overrun_title": "\U0001f6a8 {label}の上限に到達しました",
    "notify.current": "現在 {val:.0f}%",
    "notify.current_over": "現在 {val:.0f}% (100%超過)",
    "notify.reset": "リセット: {local}",
    "notify.periodic_title": "\U0001f4ca Claude 利用量 定期通知",
    "notify.current_title": "\U0001f4ca Claude 現在の利用量",
    "notify.body": "5時間: {five}  |  7日間: {seven}",
    "notify.muted_list": "ミュート中: {labels}",

    "tooltip.error": "取得失敗: {error}",

    "log.app_started": "アプリを起動しました。",
    "log.app_started_ver": "アプリを起動しました。(v{version})",
    "log.csv_write_failed": "CSV 書き込み失敗: {err}",
    "log.alert": "通知: {title} / {body}",
    "log.periodic": "定期通知: {body}",
    "log.config_save_failed": "設定保存失敗: {err}",
    "log.periodic_changed": "定期通知を {label} に変更しました。",
    "log.language_changed": "言語を {label} に変更しました。",
    "log.mute_on": "{label}: リセットまで通知ミュート",
    "log.mute_off": "{label}: ミュート解除",
    "log.usage_reset": "{label}: 利用量のリセットを検出、アラート状態をクリア",
    "log.csv_not_yet": "CSV 保存: usage.csv がまだ存在しません。",
    "log.csv_saved": "CSV を {dest} に保存しました。",
    "log.csv_save_failed": "CSV 保存失敗: {err}",

    "dialog.save_csv_title": "使用率CSVを保存",
    "dialog.csv_default_name": "claude_usage_{date}.csv",
    "dialog.csv_filetype": "CSV",
    "dialog.all_filetypes": "すべてのファイル",

    "error.unsupported_platform": "対応プラットフォームは Windows / macOS のみです。",
}

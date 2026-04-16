# Claude Usage Notifier

[English README here](README.md)

Windows / macOS のメニューバー（トレイ）に常駐し、Claude Code の Pro/Max プラン使用量をモニタリングしてトースト通知を出す常駐アプリです。

- **5時間枠 / 7日間** の残り使用率を 60 秒ごとにポーリング
- 使用率に応じてトレイアイコンのリングゲージが色付きで埋まる（視認だけで状況把握）
- 80% / 90% / 100% 到達時にトースト通知、100% 超過中は 5 分ごとに再通知
- 定期通知（30 分ごと / 1 時間ごと / オフ）をトレイメニューから切替
- 使用率は CSV に追記されるので後からグラフ化可能
- **英語 / 日本語 UI 対応** — 既定は英語、日本語ロケール環境は自動判定、`config.json` で明示指定も可能

ウィンドウは開きません。操作はすべてトレイアイコンの右クリックメニューから行います。

## 仕組み

Claude Code がログイン時に保存する OAuth トークン（`%APPDATA%\Claude\.credentials.json` 等）を読み取り、Anthropic の内部エンドポイント `api.anthropic.com/api/oauth/usage` を 60 秒ごとに叩いて使用率を取得します。**API キー不要**、Claude Code にサブスクでログイン済みなら追加設定は要りません。

## 前提

- **Windows 10 / 11** または **macOS 12+**
- Python 3.11+
- Claude Code に **サブスク（Pro/Max）でログイン済み**であること
- `python --version` が通ること

### プラットフォーム差異

| 項目 | Windows | macOS |
|---|---|---|
| 通知バックエンド | win11toast（トースト） | `osascript`（通知センター） |
| 通知の無音化 | 対応 | システム設定依存（通知音を OS 側で切る必要あり） |
| 設定ディレクトリ | `%APPDATA%\ClaudeUsageNotifier\` | `~/Library/Application Support/ClaudeUsageNotifier/` |
| 資格情報の探索 | `%APPDATA%\Claude\.credentials.json` など | 加えて `~/Library/Application Support/Claude/.credentials.json`、`~/.claude/.credentials.json` |
| スタートアップ自動起動 | `register_startup.ps1`（PyInstaller + スタートアップフォルダ） | `register_startup.sh`（launchd LaunchAgent） |

## セットアップ

### インストール

グローバル環境を汚したくないので venv を使います。

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

`requirements.txt` は `sys_platform` マーカーで OS 依存パッケージ（`win11toast` / `pyobjc`）を分岐済みです。

### 起動（開発・動作確認用）

Windows:

```powershell
python src\claude_usage_notifier.py
```

macOS:

```bash
python src/claude_usage_notifier.py
```

トレイ（メニューバー）にアイコンが表示され、60 秒後に初回ポーリングが走ります。

### スタートアップ自動起動

**Windows:**

```powershell
.\register_startup.ps1
```

初回はプロジェクト直下に `.venv` を作り、その中で PyInstaller を実行して `dist\claude_usage_notifier.exe` をビルド、スタートアップフォルダにショートカットを作成します。次回ログインから自動起動（exe 化しているので実行時に venv も Python も不要）。解除は `-Unregister`。

**macOS:**

```bash
chmod +x register_startup.sh
./register_startup.sh
```

初回は `.venv` を作成して依存パッケージを入れ、`~/Library/LaunchAgents/com.claude-usage-notifier.plist` を生成して `launchctl bootstrap` で登録します。次回ログインから自動起動（即時起動もします）。

解除：

```bash
./register_startup.sh --unregister
```

launchd の標準出力・エラーは `~/Library/Application Support/ClaudeUsageNotifier/launchd.{out,err}.log` に出ます。

## バージョンアップ（更新）

**Windows (PowerShell):**

```powershell
.\update.ps1
```

**macOS (bash/zsh):**

```bash
./update.sh
```

最新ソースの取得、依存パッケージの更新、再ビルド（Windows: exe）、アプリの再起動をまとめて行います。Windows では実行中のプロセスを自動で停止してから再ビルドします。

| フラグ | Windows | macOS | 効果 |
|---|---|---|---|
| ローカルインストール | `-Local` | `--local` / `-l` | `git pull` をスキップし、現在の作業ツリーからビルド |
| 開発モード | `-Dev` | `--dev` / `-d` | exe ビルド・スタートアップ登録をスキップ（venv 更新のみ） |

フラグは併用可。使用例:

```powershell
.\update.ps1 -Local          # Windows: ローカルソースからビルド＆インストール
./update.sh --local           # macOS: 同上
.\update.ps1 -Local -Dev     # Windows: git pull なし、venv 更新のみ
./update.sh --local --dev     # macOS: 同上
```

## 通知ルール

| 種別 | タイミング | 音 |
|---|---|---|
| 閾値通知 | 80% / 90% / 100% を**跨いだ瞬間**に 1 回ずつ | 鳴る |
| 100% 超過中 | 5 分ごとに再通知 | 鳴る |
| 定期通知 | 毎時 0 分 / 30 分に現在の使用率（既定） | **無音** |

- 5時間枠と 7日間は独立して状態管理。片方だけミュートできる
- リセット時刻（API の `resets_at`）が更新されるとミュート状態も自動で解除される
- トレイメニュー「次のリセットまでミュート」から枠ごとにトグル（チェック中＝ミュート中）
- 定期通知は右クリックメニュー「定期通知」から **オフ / 30 分ごと / 1 時間ごと** を即時切替（`config.json` に保存）

> 通知本体のアプリ名は **Claude Usage Alert** として表示されます（Windows の通知センター上部）。

## トレイアイコン

起動時に `app_icon.png` を設定フォルダに生成し、以下の表示をリアルタイム更新します。

### ゲージの色

外周リングは 5時間枠 / 7日間のうち**最大使用率**を示します。

| 状態 | 色 |
|---|---|
| 80% 未満 | ティール（緑） |
| 80% 以上 | 黄 |
| 90% 以上 | オレンジ |
| 100% 以上 | 赤 |

中心のコーラル色はアプリ識別用（Claude カラー）。

### 右クリックメニュー

- `5h: XX%` / `7d: XX%`（最新値の表示、クリック不可）
- **今すぐチェック** — 使用率を手動で再取得
- **現在の使用量を通知** — 今の値をトーストで確認（無音）
- **定期通知** — オフ / 30 分ごと / 1 時間ごと
- **次のリセットまでミュート** — 5時間枠 / 7日間 をそれぞれトグル（次のリセットで自動解除）
- **設定ファイルを開く** / **ログを開く** — メモ帳などで開く
- **使用率CSVを保存...** — 保存ダイアログで任意の場所にコピー
- **終了**

## 保存されるファイル

設定ディレクトリの下にまとまります（Windows: `%APPDATA%\ClaudeUsageNotifier\` / macOS: `~/Library/Application Support/ClaudeUsageNotifier/`）：

| ファイル | 内容 |
|---|---|
| `config.json` | 定期通知間隔・UI 言語などの設定 |
| `app.log` | 起動・通知・エラーのテキストログ（追記、ローテーション無し） |
| `usage.csv` | ポーリングごとの使用率履歴（後述） |
| `app_icon.png` | トースト通知に使うアプリアイコン |

### usage.csv の形式

ポーリング成功ごとに 1 行追記。列構成：

| 列 | 内容 |
|---|---|
| `timestamp` | ローカル時刻（ISO 8601、秒精度） |
| `five_hour_pct` | 5時間枠の使用率（％） |
| `five_hour_resets_at` | 5時間枠のリセット時刻（UTC ISO） |
| `seven_day_pct` | 7日間の使用率（％） |
| `seven_day_resets_at` | 7日間のリセット時刻（UTC ISO） |

60 秒ポーリングなので 1 日あたり約 1440 行（~80 KB）。Excel / pandas でそのまま読めます。肥大化が気になれば手動で退避してください（ローテーション無し）。

## UI 言語

トレイメニュー・通知・ログメッセージはローカライズ対応。`config.json`:

```json
{
  "periodic_notification_minutes": 30,
  "language": "auto"
}
```

| 値 | 挙動 |
|---|---|
| `"auto"` | システムロケールから自動判定（日本語環境 → `ja`、それ以外は `en`） |
| `"en"` | 英語（デフォルト） |
| `"ja"` | 日本語 |

変更後はアプリを再起動してください。言語を追加する場合は `src/notifier/locales/<コード>.py` に `STRINGS` dict を置き、`src/notifier/i18n.py` に登録します。

## プロジェクト構成

```
src/
  claude_usage_notifier.py      # エントリ
  notifier/                     # パッケージ
    app.py                      # メインアプリ（常駐ループ、通知判定）
    config.py                   # 設定ロード/保存
    constants.py                # 定数（プラン定義など）
    i18n.py                     # 翻訳ルックアップ（t / set_language）
    locales/                    # 翻訳リソース（en.py, ja.py）
    notifications.py            # 通知マネージャ（バックエンドに委譲）
    platform_integration.py     # OS 依存処理（通知バックエンド、パス、ファイル起動）
    plan_usage.py               # Usage API ポーリング
    tray.py                     # pystray メニュー
    usage_log.py                # CSV ロギング
    utils.py                    # 小物
register_startup.ps1            # Windows: PyInstaller ビルド＆スタートアップ登録
register_startup.sh             # macOS: launchd LaunchAgent 登録
update.ps1                      # Windows: ワンコマンド更新（pull・再ビルド・再起動）
update.sh                       # macOS: ワンコマンド更新（pull・依存更新・再起動）
requirements.txt                # sys_platform で OS 依存パッケージを分岐
```

OS 依存コードは原則 `platform_integration.py` にまとめています。新しい OS を追加する場合は、そこに backend / パス解決を足すだけで他モジュールは変えずに済むようにしてあります。

## 注意

- `api.anthropic.com/api/oauth/usage` は**非公式エンドポイント**です。Anthropic のアップデートで変更・廃止される可能性があります
- macOS 版は osascript 経由のシンプルな通知のみ。無音フラグなどは OS 設定依存

## ライセンス

MIT License — [LICENSE](LICENSE) を参照してください。

## 免責事項

このツールは Anthropic の非公開エンドポイントを利用しています。**自己責任**でご利用ください。作者はアカウントの問題・API 変更・サービス停止等に関して一切の責任を負いません。

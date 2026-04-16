# version-check.yml

PR 時にバージョン番号が更新されているかを検証するワークフロー。

## 基本情報

| 項目 | 値 |
|---|---|
| ファイル | `.github/workflows/version-check.yml` |
| ワークフロー名 | `Version bump check` |
| job 名 | `check` |
| トリガー | `main` ブランチ向けの Pull Request |
| 実行環境 | `ubuntu-latest` |
| 必要な権限 | デフォルト（read） |

## 目的

`main` へのマージ時にバージョンアップを必須にする。`src/notifier/__init__.py` の `__version__` が main ブランチより上がっていなければ CI を失敗させ、マージをブロックする。

## 処理フロー

### Step 1: チェックアウト

```yaml
uses: actions/checkout@v4
with:
  fetch-depth: 0
```

`fetch-depth: 0` で全履歴を取得する。main ブランチの `__init__.py` を `git show` で参照するために必要。

### Step 2: PR ブランチのバージョン取得

```bash
ver=$(sed -n 's/^__version__\s*=\s*"\([^"]*\)"/\1/p' src/notifier/__init__.py)
```

ワーキングツリー（= PR ブランチ）の `__init__.py` から `__version__` を抽出する。

- 出力: `steps.pr.outputs.version` (例: `0.2.0`)

### Step 3: main ブランチのバージョン取得

```bash
ver=$(git show origin/main:src/notifier/__init__.py | sed -n 's/^__version__\s*=\s*"\([^"]*\)"/\1/p')
```

`git show` で main ブランチ上のファイルを直接読み取る。チェックアウトの切り替えは不要。

- 出力: `steps.main.outputs.version` (例: `0.0.1`)

### Step 4: バージョン比較

```bash
HIGHER=$(printf '%s\n%s' "$MAIN_VER" "$PR_VER" | sort -V | tail -n1)
```

`sort -V`（バージョンソート）で 2 つのバージョンを比較する。ソート後の最終行が main のバージョンと同じなら、PR 側が上がっていないと判定する。

| 条件 | 結果 |
|---|---|
| PR > main (例: `0.0.2` > `0.0.1`) | Pass |
| PR = main (例: `0.0.1` = `0.0.1`) | **Fail** |
| PR < main (例: `0.0.1` < `0.0.2`) | **Fail** |

失敗時は `::error::` アノテーションで現在の main バージョンを表示する。

## エラーケース

| ケース | 挙動 |
|---|---|
| `__version__` が読み取れない | `Could not read __version__` エラーで失敗 |
| main に `__init__.py` が存在しない | `git show` が失敗し、main 側のバージョンが空文字になる。PR 側にバージョンがあれば Pass |
| バージョンが上がっていない | エラーメッセージで現在の main バージョンを案内 |

## ブランチ保護との連携

このワークフローの job 名 `check` を Required status check に登録すると、バージョンアップなしの PR はマージ不可になる。

設定手順: Settings > Branches > Branch protection rules > `main` > Require status checks to pass before merging > `check` を追加

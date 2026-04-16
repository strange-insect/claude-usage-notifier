# release.yml

main マージ後に README 同期・タグ作成・GitHub Release を自動で行うワークフロー。

## 基本情報

| 項目 | 値 |
|---|---|
| ファイル | `.github/workflows/release.yml` |
| ワークフロー名 | `Release` |
| job 名 | `release` |
| トリガー | `main` ブランチへの push |
| 実行環境 | `ubuntu-latest` |
| 必要な権限 | `contents: write` |
| 使用する Secret | `GITHUB_TOKEN`（自動提供） |

## 目的

main にマージされたら以下を自動で実行する:

1. README のバージョン表記を `__init__.py` に合わせて同期
2. `vX.Y.Z` 形式の git タグを作成
3. コミットログから Release Note を生成し GitHub Release を公開

## 処理フロー

### Step 1: チェックアウト

```yaml
uses: actions/checkout@v4
with:
  fetch-depth: 0
  token: ${{ secrets.GITHUB_TOKEN }}
```

- `fetch-depth: 0`: 全履歴とタグを取得（前タグとの比較、タグ存在チェックに必要）
- `token`: README 同期コミットを push するために必要

### Step 2: バージョン読み取り

```bash
ver=$(sed -n 's/^__version__\s*=\s*"\([^"]*\)"/\1/p' src/notifier/__init__.py)
```

`src/notifier/__init__.py` から `__version__` を抽出する。

- 出力:
  - `steps.ver.outputs.version` (例: `0.2.0`)
  - `steps.ver.outputs.tag` (例: `v0.2.0`)

### Step 3: タグ重複チェック

```bash
git rev-parse "$TAG" >/dev/null 2>&1
```

同じタグが既に存在するかを確認する。

- 出力: `steps.tag_check.outputs.exists` (`true` / `false`)
- `true` の場合、以降のすべてのステップをスキップする（冪等性の確保）

**スキップ条件**: 以降の全ステップに `if: steps.tag_check.outputs.exists == 'false'` が付与されている。

### Step 4: README バージョン同期

```bash
sed -i "s|<!-- version-badge -->.*<!-- /version-badge -->|<!-- version-badge --><strong>Version ${VER}</strong><!-- /version-badge -->|" README.md
sed -i "s|<!-- version-badge -->.*<!-- /version-badge -->|<!-- version-badge --><strong>Version ${VER}</strong><!-- /version-badge -->|" README.ja.md
```

README 内の `<!-- version-badge -->...<!-- /version-badge -->` マーカー間を置換する。マーカー外のバージョン言及には影響しない。

置換後の差分チェック:

| 差分 | 挙動 |
|---|---|
| あり | `github-actions[bot]` としてコミット & push |
| なし | `READMEs already in sync.` を出力してスキップ（空コミットは作らない） |

コミットメッセージ: `Sync README version to vX.Y.Z`

### Step 5: タグ作成

```bash
git tag "$TAG"
git push origin "$TAG"
```

`vX.Y.Z` 形式の軽量タグ（lightweight tag）を作成して push する。Step 4 で追加コミットがあった場合、そのコミットにタグが付く。

### Step 6: Release Note 生成

前タグからのコミットログをもとに `release_notes.md` を生成する。

```bash
PREV_TAG=$(git tag --sort=-v:refname | grep -v "^${TAG}$" | head -n1)
```

前タグの検出はバージョンソートの降順で、今回のタグを除いた最新を取得する。

| 条件 | 挙動 |
|---|---|
| 前タグあり | `PREV_TAG..TAG` の範囲でコミットログを取得。Full Changelog の比較リンクを付与 |
| 前タグなし（初回） | タグ単体のログを取得。`**Initial release**` と表示 |

コミットログのフィルタ:

- `--no-merges`: マージコミットを除外
- `Sync README version` を含む行を除外（自動コミットのノイズ除去）
- `Co-Authored-By:` を含む行を除外

### Step 7: GitHub Release 作成

```bash
gh release create "$TAG" --title "$TAG" --notes-file release_notes.md
```

`gh` CLI で GitHub Release を作成する。タイトルは `vX.Y.Z`、本文は Step 6 で生成した Release Note。

## 冪等性

このワークフローは同じバージョンに対して複数回実行されても安全。

| 状況 | 挙動 |
|---|---|
| タグが既に存在 | Step 3 で検知し、以降すべてスキップ |
| README に差分なし | Step 4 でコミットせずスキップ |
| Release が既に存在 | タグ存在チェックでスキップされるため到達しない |

## 自動コミットの識別

README 同期による自動コミットは以下で識別できる:

- コミッター: `github-actions[bot]`
- メッセージ: `Sync README version to vX.Y.Z`

Release Note 生成時にこのコミットは自動で除外される。

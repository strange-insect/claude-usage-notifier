# バージョン管理ガイド

## バージョニング規則

[Semantic Versioning](https://semver.org/) に従う。

| 桁 | 意味 | 例 |
|---|---|---|
| MAJOR | 後方互換性のない変更 | 設定ファイル形式の変更など |
| MINOR | 後方互換性のある機能追加 | 新しい通知オプションの追加など |
| PATCH | バグ修正・軽微な改善 | 通知タイミングの修正など |

## バージョンの定義箇所

| ファイル | 役割 | 更新方法 |
|---|---|---|
| `src/notifier/__init__.py` | **Single Source of Truth** — `__version__` 変数 | 開発者が手動で更新 |
| `README.md` / `README.ja.md` | 表示用 | main マージ時に [release.yml](../actions/release.md) が自動同期 |

開発者が変更するのは `__init__.py` の1行のみ。

## バージョンの表示箇所

| 場所 | 表示例 | ソース |
|---|---|---|
| トレイメニュー（Quit の上） | `v0.0.1` | `__init__.py` を実行時に参照 |
| 起動ログ | `アプリを起動しました。(v0.0.1)` | 同上 |
| update スクリプト実行時 | `Version: v0.0.1` / `Updated: v0.0.1 -> v0.2.0` | `__init__.py` を sed で読み取り |
| README 冒頭 | `<strong>Version 0.0.1</strong>` | マーカーコメント内 |

## リリース手順

### 1. バージョンを上げる

```python
# src/notifier/__init__.py
__version__ = "0.2.0"  # ← ここを変更するだけ
```

README は触らなくてよい（マージ後に自動同期される）。

### 2. PR を作成してマージ

1. main 向け PR を作成
2. [version-check.yml](../actions/version-check.md) がバージョンアップを検証 → Pass を確認
3. マージ

### 3. 自動リリース（マージ後）

[release.yml](../actions/release.md) が以下を自動実行:

1. README のバージョンを同期（差分がある場合のみコミット）
2. `vX.Y.Z` タグを作成
3. GitHub Release を公開（コミットログから Release Note を生成）

### バージョンの上げ方の目安

```
# バグ修正
__version__ = "0.0.1"  →  __version__ = "0.0.2"

# 機能追加
__version__ = "0.0.2"  →  __version__ = "0.1.0"

# 破壊的変更
__version__ = "0.2.0"  →  __version__ = "1.0.0"
```

## README のバージョンマーカー

README 内のバージョン表記は HTML コメントで囲まれている:

```markdown
<!-- version-badge --><strong>Version 0.0.1</strong><!-- /version-badge -->
```

- `release.yml` はこのマーカー間のみを置換する
- マーカー外のバージョン言及（例: 「v0.0.1 で追加された機能」）には影響しない
- マーカーを削除・変更すると自動同期が壊れるので注意

## ワークフロー全体像

![Versioning & Release Workflow](https://kroki.io/plantuml/svg/VLHjQzjM5Fukq7yuj50ImvoKRNJ8i3LnecsKPi6ZtJe2uiQwjkyYNndfEY4i_N0bIEF4eKwsEYqDIyV6F3Bi1bhO2-doOqxbf9_w5yQLRDUEsIHzqJcFpdcUvvohcxuWdgYM7LtpLnYl48-KOPdaLugUM-LsrdLS3wwQy-eUXlWbOhjhZ1UXG1oV3gTiMY1LHvWk5mkaJE7AbxJeKhZp-PLX5CaBjih4EdodQm2pOnsdpGzCCqwvdaszNlZ3sHjpizTLM9Nl1T-FBnMSOwJiSdkyccb-D7zz635Sr3HdfgUdTUt-23_FSzSISfTwtzSrNHDCE1JkKizdBbSsN8CSTIZnANpbUYi5nrrJi8qvkaeTjqAz3LsBhTOrmwH4L3qAonxX-HAWRBrfxfm_-JkZQuRlvQUuArY1KM_AiXXdmhBIbVKbdafPrchIpx9IAS1Wl_lqPRTvaj4rxWeA7YkMXEABylluUOPoB_gbrdtw4kKJ3EeeJxwufG2v-Pcvs_E0yld5W-Devn7ALjIeTm-FK3vIk617roYtGPNLDQDC68UeiOTo3-Nli9Y3rwyEkrkDJApmKoO-gox3J5umb_iRkcOCUBwNBz7yIdgzx5WMH9sZYv_gIkDY3b1sO4YE4XCzR4R_76Jw_VuFeMki01EBEVWOOkmdao1AbCF4FUfFAe5NAyIXHOzIRcGL1QWGtwTsHjUeurEOM70Jc6bcizbi3rCWpA7s4f_0y4SCJp7u4yCcXcqCGmoUJsRK5oFp130kCNnzrkcsVqPvWFBNQ7CNAbM_b7mtvXA04MtkOYWnQ2KTOg1D1ScNOljPOMo3Okk2_G71_vw0bopZcFUN25ySjr6UHG-R66mFZ8qQTPIFCJZ3u0HbFMe_ZWv_6_FOmE0l369tmeEtfrlHvl5vk_Rsj1Rhy8LR6N5x8CX8jYzTjc6gjudfRubwHTbPuXWs-kQtC7oXnjvGg_cEtH-TQ6iJPO31zZYfYxDNqVOp35vWU1HJsu9h_J6Cp7w4laeE-1MP046Aa4gjVfs-b_ucEMl9ohyhPaIrtRv5EnZKK7Q6kwgzKQdM4k__5nRK8SLW__o7e-Jm6Bt1zG63Bh7Mn45TkqcvNIqx_m8)

各ワークフローの詳細仕様:

- [version-check.yml](../actions/version-check.md) — PR 時のバージョンチェック
- [release.yml](../actions/release.md) — main マージ後の自動リリース

## ブランチ保護の設定

`main` ブランチに以下の保護ルールを推奨:

1. **Settings > Branches > Add branch protection rule**
2. Branch name pattern: `main`
3. **Require status checks to pass before merging** にチェック
4. Status checks に `check` (`version-check.yml` の job 名) を追加

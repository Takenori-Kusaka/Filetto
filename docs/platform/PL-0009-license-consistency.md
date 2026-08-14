# PL-0009: README を Filetto のものにし、ライセンス宣言の食い違いを検査する

対象 Issue: [#112](https://github.com/Takenori-Kusaka/Filetto/issues/112)
作成: 2026-08-14 / レーン: Platform

## 1. 直したこと

| # | 依頼 | 対応 |
| --- | --- | --- |
| 1 | ライセンス節を実態へ直す | **完了。** コード AGPL-3.0-or-later / 文書 CC BY 4.0 |
| 2 | 「ライセンスは自由に決められます」を削る | **完了** |
| 3 | Filetto の説明を書く | **完了。** 冒頭に配置 |
| 4 | セットアップは「準備中」と明記する | **完了。** [#113](https://github.com/Takenori-Kusaka/Filetto/issues/113) を参照先として明記 |
| — | 検査の提案 | **採りました。** `license-consistency`(§2) |

**README の構成を入れ替えました。** 冒頭がテンプレートの説明でプロダクトの説明が無い状態でした。**Filetto の説明を先頭に置き、プロセスの説明は後段へ移して「Filetto を使うだけなら読む必要はありません」と明記しました。**

## 2. 検査: 4つの宣言を突き合わせます

```
$ node scripts/gate/license-consistency.mjs
突き合わせた宣言:
  pyproject.toml(正本)       code = AGPL-3.0-or-later
  README.md                code = AGPL-3.0-or-later / docs = CC-BY-4.0
  LICENSE                  AGPL-3.0-or-later(見出し一致)
  LICENSE-docs             CC-BY-4.0(見出し一致)
::notice::license-consistency: 4 件を突き合わせ、0 件の食い違いを検出
```

| 突き合わせ | 検出できるもの |
| --- | --- |
| `pyproject.toml` ↔ `README.md` | **本件の事例。** 片方だけ書き換えた |
| SPDX 識別子 ↔ 全文の見出し | 識別子を直して**全文を差し替え忘れた** |
| 宣言の存在 | README から宣言が消えた |

### README の文章から推測しません

**機械可読な宣言を1行置きます。**

```markdown
<!-- license: code=AGPL-3.0-or-later docs=CC-BY-4.0 -->
```

**文章から推測すると、書き換えの取りこぼしを検出できません。** 「MIT」という語が別の文脈で残っていても、あるいは消えていても、宣言が正しいかは判定できません。**宣言が無ければ落とします。**

### 正本は `pyproject.toml` です

**コードのライセンスの正本を1つに決めます。** README がそれと食い違えば落ちます。**どちらが正しいかを検査が決めるのではなく、正本がどれかを先に決めています。**

## 3. 検証

```
$ node scripts/gate/license-consistency.mjs   → 4 件、食い違い 0 件
$ pytest tests/gate                           → 76 passed
$ ruff / spec-lint / double-encoding / drift  → すべて緑
```

否定側6件:

| # | 壊し方 | 結果 |
| --- | --- | --- |
| 1 | **README だけ MIT のまま残す**(本件の事例) | 落ちた |
| 2 | **README から宣言を消す** | 落ちた |
| 3 | **識別子は AGPL のまま、LICENSE 全文を MIT に差し替える** | 落ちた |
| 4 | `pyproject.toml` から license を消す | 落ちた |
| 5 | `LICENSE` を消す | 落ちた |
| 6 | 設定ファイルを消す | 落ちた |

**一時ディレクトリへ写して壊しています。本物のファイルは書き換えていません。**

## 4. 残っていること

**セットアップ手順は書けません。** `docker-compose.yml` が未作成のためです([#113](https://github.com/Takenori-Kusaka/Filetto/issues/113))。**「準備中」と明記し、いまの状態(G-4 待ち・実装コードなし)も書きました。空欄にしていません。**

## 5. 参照

- [#112](https://github.com/Takenori-Kusaka/Filetto/issues/112) — 本件の依頼
- [ADR-0001](../../context/decisions/0001-license-agpl-3.md) — コードを AGPL とした判断
- [#113](https://github.com/Takenori-Kusaka/Filetto/issues/113) — `docker-compose.yml`

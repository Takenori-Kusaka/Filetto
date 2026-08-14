# 判断記録(ADR)

**あとから変えにくい決定の経緯を記録します。**

**立ち戻る先は本ディレクトリではありません。** **[`context/standards/product-principles.md`](../standards/product-principles.md)(プロダクトの軸)です。**

| | 用途 | 案を書くか |
| --- | --- | --- |
| **プロダクトの軸** | **困ったときに立ち戻る。決まったことだけ** | **書かない** |
| **判断記録(ADR)** | **その軸に至った経緯。採らなかった選択肢とその理由** | **書く** |

## 索引

**生きているもの**

| ADR | 決めたこと | 対応する軸 |
| --- | --- | --- |
| [0001](0001-license-agpl-3.md) | ライセンスを AGPL-3.0 とする | **軸2** |
| [0002](0002-external-interface-contract.md) | 対外インターフェース契約(REST / MCP)。安定 ID・本文と署名付き URL の両方・HTTP と stdio | **軸7** |
| [0003](0003-reversible-file-operations.md) | 破壊的操作をすべて可逆にする。ゴミ箱方式 | **軸1・軸3** |
| [0004](0004-jwt-claims-contract.md) | JWT クレーム契約。検証の責務分界 | **軸7** |
| [0005](0005-indexer-selection.md) | 検索構成を案B(パース + BM25 / e5-small)とする | — |
| [0006](0006-implementation-stack.md) | Python バックエンド + TypeScript フロント | — |
| [0008](0008-lore-as-versionstore.md) | VersionStore に Lore を採用する | 軸3 の手段 |
| [0009](0009-claude-code-permissions-no-ask.md) | 権限設定から `ask` を廃す | — |
| [0010](0010-database-layer.md) | データベース層。SQLite + BLOB 列 | — |
| [0011](0011-ocr-correction-and-figures.md) | OCR の誤り訂正と図表の扱い | **軸5** |
| [0012](0012-line-limit-scope.md) | 行数上限を判断記録・機能仕様・設計文書へ適用しない | — |
| [0013](0013-license-check-spdx-expression.md) | ライセンス検査を SPDX 式の評価へ移す | — |
| [0014](0014-standard-scope-misapplication.md) | 標準の条項を適用範囲ごと確認してから課す | — |
| [0015](0015-enforcement-scope-during-optimization.md) | 最適化期間中は強制層を戻さない(**決定1 は 0019 が置き換え**) | — |
| [0016](0016-change-size-as-target-not-limit.md) | 変更規模の数値を目標の目安とし、合否の条件にしない | — |
| [0017](0017-one-click-verification-placement.md) | 「確かめる箇所へ1クリック」の受入基準を F-003 へ置く | **軸4** |
| [0019](0019-block-what-diffs-cannot-show.md) | 差分に出ないものだけを `deny` で止める | — |

**置き換えられたもの — 本文を読む必要はありません**

| ADR | 置き換え先 |
| --- | --- |
| [0007](0007-allowed-licenses.md) 依存関係の許可ライセンス一覧を補正する | **[0013](0013-license-check-spdx-expression.md)** |

**欠番**

| 番号 | 経緯 |
| --- | --- |
| **0018** | **用語と文言の単一正本。決定されないまま `main` へ入り、取り消した**([#142](https://github.com/Takenori-Kusaka/Filetto/pull/142) でマージ / [#152](https://github.com/Takenori-Kusaka/Filetto/pull/152) で削除)。**決定の場所は `specs/F-003/plan.md`。判定は G-4**([#131](https://github.com/Takenori-Kusaka/Filetto/issues/131)) |

**番号は再利用しません。**

**削除した理由**: **一度も採用されていない ADR です。** 「採用済みの ADR を書き換えない」は、**採用した決定を守るための規約であり、採用に至らなかった草稿を残す要求ではありません。**

**廃止として残す案も採りませんでした。** **廃止した ADR がディレクトリに並ぶこと自体が、本来の目的(困ったときに立ち戻る)を妨げます。** **18本を順に開く状態を作った原因の1つです。**

**検討の中身(6形式の比較)は [#142](https://github.com/Takenori-Kusaka/Filetto/pull/142) と履歴に残ります。** **`specs/F-003/plan.md` から参照できます。**

## ADR にする基準

**次の1つ以上に当てはまるときだけ書きます。**

| # | 基準 |
| --- | --- |
| 1 | **戻すのに、他の成果物の書き換えが要る**(対外インターフェース・スキーマ・ライセンス) |
| 2 | **採らなかった選択肢を残さないと、同じ検討が繰り返される** |
| 3 | **標準や規約の解釈を変える** |

**1つも当てはまらないなら、`plan.md` か `docs/platform/PL-NNNN` か PR 本文へ書きます。**

**可逆であることを自分で確認できる決定は、ADR にしません。** **欠番の 0018 は、本文に「可逆です」と書きながら ADR にしました。基準を先に持っていれば、書いていません。**

**2026-08-14 時点で 18本。実装コードは0行です。** **うち7本がプロセス自身についての判断です。** **本基準は、この比率を繰り返さないために置きます。**

## 命名

`NNNN-<英語のケバブケース>.md`。4桁のゼロ埋め連番。番号は再利用しません。

```
0001-use-postgres.md
0002-session-in-cookie.md
```

## 書き方

`/adr-write` を使うか、`templates/02-adr.md` を写します。

## 採用済みの ADR を書き換えない

決定を変えるときは**新しい ADR で置き換えます**。古い ADR のステータスを「置き換え(→ ADR-NNNN)」にして後継へリンクし、本文はそのまま残します。

書き換えると、当時なぜそう決めたのかが失われます。**採らなかった選択肢を書き残すことは、後任者が同じ検討を繰り返さないための唯一の手段です**。

## コア機能では添付が必須

コア機能の変更では、独立レビュー(G-6)で該当の ADR を添付します。

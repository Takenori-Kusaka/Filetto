# ADR-0007: 依存関係の許可ライセンス一覧を補正する

## ステータス

採用(2026-08-12)

**本 ADR の一部は暫定です。** [pit-in-template#13](https://github.com/Takenori-Kusaka/pit-in-template/issues/13) の修正後に見直します(下記「期限」)。

**一部置き換え(→ [ADR-0013](./0013-license-check-spdx-expression.md))。** 置き換えの範囲は「表記の吸収(暫定)」の6件と「期限」節に限る。それ以外の決定・記録は有効なまま残る。

## コンテキスト

G-5 基準5(依存関係のライセンス検査 / `ip-clearance`)が、**ライセンス上の問題がない状態で失敗します**。

`adapters/python.json` の検査コマンドは次のとおりです。

```
pip-licenses --format=json --allow-only="$PIT_IN_ALLOWED_LICENSES"
```

`PIT_IN_ALLOWED_LICENSES` は `process.config.json` の `ci.allowedLicenses` を `;` で連結したもので、初期値は **SPDX 識別子**(`MIT` / `Apache-2.0` / `BSD-2-Clause` / `BSD-3-Clause` / `ISC`)です。

一方 `pip-licenses` が報告するのは **PyPI の classifier 文字列**(`MIT License` / `Apache Software License` / `BSD License`)または **SPDX 式**(`Apache-2.0 OR BSD-2-Clause`)です。**文字列として一致しません。**

開発依存を `pytest / pytest-cov / ruff / pip-audit / pip-licenses` のみに絞った最小構成で、17件が弾かれました。性質は3種類に分かれます。

| 種類 | 例 | 実体 |
| --- | --- | --- |
| **1. 表記の不一致** | `MIT License` / `Apache Software License` / `BSD License` / `Apache-2.0 OR BSD-2-Clause` | **すべて許可範囲内**。名前が違うだけ |
| **2. 一覧にない許諾型** | certifi = MPL-2.0、defusedxml = PSF License | 一覧に無いが、実務上は許容される部類 |
| **3. 自プロジェクト自身** | **filetto = AGPL-3.0-or-later** | `pip install -e .` で自分自身が入るため弾かれる |

**種類3 は明確な不具合です。** `allowedLicenses` は依存関係に許すライセンスの一覧であり、自プロジェクトのライセンスとは別の概念です。AGPL や GPL でプロダクトを公開する利用者は必ずこれに当たります([[0001-license-agpl-3]])。

この状態でドキュメントのみの PR(18コミット)がマージできず滞留しています。

## 決定

`process.config.json` の `ci.allowedLicenses` を次のとおり補正します。**判定の実体を緩める変更と、表記を吸収する変更を、意図として区別します。**

### 追加するもの(実体の変更。恒久)

| 追加 | 理由 |
| --- | --- |
| `MPL-2.0` | ファイル単位のコピーレフト。改変したファイルの公開義務にとどまり、リンクした側の配布条件へ波及しない。AGPL-3.0 の本プロダクトと両立する。実際の依存は certifi(HTTPS の CA 証明書束) |
| `PSF-2.0` | Python Software Foundation License。許諾型。実際の依存は defusedxml |
| `AGPL-3.0-or-later` | **自プロジェクト自身**。依存関係に AGPL を許す意図ではない。`pip install -e .` が自分自身を検査対象に含めることへの対処 |

### 追加するもの(表記の吸収。暫定)

`pip-licenses` の classifier 表記を併記します。**実体としては上記および既存の許可範囲と同一です。**

`MIT License` / `Apache Software License` / `BSD License` / `Apache-2.0 OR BSD-2-Clause` / `Mozilla Public License 2.0 (MPL 2.0)` / `Python Software Foundation License`

**これは汚い回避策です。** 本来はツール側で正規化すべきものであり、[pit-in-template#13](https://github.com/Takenori-Kusaka/pit-in-template/issues/13) として起票済みです。

### 期限

**#13 が修正され、正規化された照合が入った時点で、「表記の吸収」として追加した項目をすべて削除します。** 削除後に `ip-clearance` が通ることを確認し、本 ADR を改訂します。

この期限を D-0 の次回レビュー期日(2026-11-12)の確認項目に含めます。

## 検討した選択肢

| 案 | 採らなかった理由 |
| --- | --- |
| **テンプレート側の修正(#13)を待つ** | 正しいが、修正時期が読めない。18コミットの滞留を無期限に延ばすことになる。**「待つ」を選ぶには滞留のコストが高すぎる** |
| **`adapters/python.json` の検査コマンドを自分で書き換える** | 根本解決だが、テンプレートの修正を先取りすることになり、#13 の修正と衝突する。テンプレートから生成したリポジトリが、テンプレート側の設計を独自に変える構図は避ける |
| **`ip-clearance` を除外・無効化する** | `CLAUDE.md` 禁止事項6(静的解析の重大度・除外設定を変える)の方向。**検査そのものを止める選択は採らない** |
| **開発依存を減らして弾かれる依存を消す** | `pip-audit`(脆弱性検査)や `pip-licenses` 自身を外すことになる。**検査を通すために検査の道具を捨てる**ことになり、本末転倒 |
| **一覧の補正(採用)** | — |

理由欄は判定者(takenori-kusaka / 技術判断者)の判断による(2026-08-12)。

## 可逆性

| 項目 | 内容 |
| --- | --- |
| 後から変えられるか | **変えられる** |
| 変えるとしたら必要なこと | `process.config.json` の1箇所を編集する。強制層で保護されているため人の操作を要する |
| いつまでなら安く変えられるか | 常時。**むしろ #13 の修正後に必ず戻す**(上記「期限」) |

## 非機能への影響

| 項目 | 影響 |
| --- | --- |
| 性能 | なし |
| 可用性 | なし |
| セキュリティ | なし。ライセンス検査の対象範囲の話であり、脆弱性検査(`pip-audit`)には影響しない |
| 運用 | **表記の吸収分が残っている間、判定がやや緩くなる**。`Apache Software License` のような classifier 表記は、実際には Apache-2.0 以外を指す可能性が理論上ある。**#13 の修正後に必ず削除する理由がここにある** |

## 事業への影響

| 項目 | 内容 |
| --- | --- |
| 顕在化が分かる兆候 | 依存に許諾型でないライセンスが混入しても `ip-clearance` が通ってしまうこと。具体的には、classifier 表記のみを持つパッケージで実体がコピーレフトである場合 |
| 回復に要する時間 | **1日**(`allowedLicenses` を厳格な SPDX のみへ戻し、照合を自前で書く) |
| 影響を受ける利用者・業務 | 本プロダクトを配布する経路すべて。AGPL-3.0 との両立が崩れた依存が混入すると、配布条件に影響する |

## 影響

**この決定によって得られるもの:**

- `ip-clearance` が通り、滞留している PR をマージできる
- MPL-2.0 と PSF-2.0 が明示的に許可範囲へ入る。これは実体として正しい設定である
- 自プロジェクト自身が弾かれる不具合を回避できる

**トレードオフ:**

- **表記の吸収分だけ、判定が緩くなる**。classifier 表記は SPDX ほど厳密ではない
- **`allowedLicenses` を読んだ人が、意図を誤解しうる**。「AGPL を依存に許している」と読める。本 ADR がその誤解を防ぐ唯一の記録である

**この決定で解決しないこと:**

- **`pip-licenses` の表記正規化**は解決していない。テンプレート側(#13)の修正を待つ
- **`node` アダプタの `license-checker-rseidelsohn`** に同種の問題があるかは未確認。TypeScript フロントエンドの検査経路を決める際([[0006-implementation-stack]])に確認する

## 関連

- [pit-in-template#13](https://github.com/Takenori-Kusaka/pit-in-template/issues/13) — 本 ADR の暫定部分を解消するための起票
- [[0001-license-agpl-3]] — 自プロジェクトが AGPL であること
- [[0006-implementation-stack]] — Python アダプタを選んだ判断
- `docs/D-0-governance.md` — 次回レビュー期日(2026-11-12)に本 ADR の期限を確認する

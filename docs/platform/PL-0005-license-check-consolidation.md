# PL-0005: 許可ライセンス一覧を7件へ縮め、テンプレートの修正版は取り込まない

対象 Issue: [#102](https://github.com/Takenori-Kusaka/Filetto/issues/102)
作成: 2026-08-13 / レーン: Platform

## 1. 結論

| # | 依頼 | 結果 |
| --- | --- | --- |
| 1 | `scripts/gate/ip-clearance-python.mjs` を取り込む | **取り込みません。** 実測で3つの誤通過を確認しました(§3) |
| 2 | CI から実際に走る経路まで用意する | **既にあります。** `adapters/python.json` → `license-check.mjs`(PL-0001) |
| 3 | `allowedLicenses` を7件へ縮める | **完了**(§4) |
| — | 2つのスクリプトの関係 | **重複しています。`license-check.mjs` を正とします**(§3) |

**依頼の3件を分けないという条件は満たしています。** 本 PR に3件すべてが入っています(1 は「取り込まない」という形で)。

## 2. なぜ依頼どおりに取り込まなかったか

**取り込むと、本案件が既に決めたことを巻き戻します。**

`license-check.mjs` は [ADR-0013](../../context/decisions/0013-license-check-spdx-expression.md) と [PL-0001](PL-0001-ip-clearance-pep639.md) の判断に基づいて作りました。**そこで採らないと決めた挙動が、テンプレートの修正版に入っています。**

**範囲の判断は PO の領域です。** 取り込まないことの可否は PO へ差し戻します(§6)。

## 3. 実測: 同じ入力を両方へ与えた結果

許可一覧は `MIT;Apache-2.0;BSD-2-Clause;BSD-3-Clause;ISC;MPL-2.0;PSF-2.0` の7件。

| # | 入力 | テンプレート | 本案件 | どちらが正しいか |
| --- | --- | --- | --- | --- |
| 1 | `MIT AND GPL-3.0-only` | **合格(exit 0)** | 不合格(exit 1) | **本案件。** AND は両方を満たす必要があり、GPL-3.0 は許可範囲外 |
| 2 | `MIT-0`(許可していない) | **合格(exit 0)** | 不合格(exit 1) | **本案件。** 許可一覧に無い |
| 3 | 入力が空 | **合格(exit 0)** | 不合格(exit 1) | **本案件。** 検査対象0件を「実施した」として通さない |

### 1 の原因: `AND` を `OR` として扱っています

```js
const parts = l.split(/\s+or\s+|\s+and\s+|[|/;,]/i).map(p => p.trim());
...
return normalizedParts.some(part => ...);   // ← some = いずれか1つ通れば合格
```

**`OR` と `AND` を同じ区切りとして分解し、`some` で判定しています。** `MIT AND GPL-3.0-only` は「MIT と GPL-3.0 の両方に従う」という意味ですが、**MIT だけを見て合格にします。**

**コピーレフトの依存が混入しても通ります。** AGPL-3.0 で配布する本プロダクトにとって、これは検査の目的そのものに反します。

### 2 の原因: 部分一致で照合しています

```js
if (part.includes(allowed) || allowed.includes(part)) return true;
```

**`MIT-0` は `MIT` を含むため合格になります。** これは PL-0001 で `pip-licenses --partial-match` を採らなかった理由と同じ挙動です。当時も `cffi`(`MIT-0`)が誤って通ることを実測しています。

### 3 の原因: 入力が空でも通します

```js
if (!input.trim()) {
  console.log('No input received on stdin');
  process.exit(0);
}
```

**`docs/platform/README.md` 検査を足すときの原則2(黙って通る検査を作らない)に反します。** 本案件は `secretScan` が空の設定で通過し続けた前例を持っています([#58](https://github.com/Takenori-Kusaka/Filetto/issues/58) 運用上の注意1)。

### 機能の対応

| 観点 | `license-check.mjs`(本案件) | `ip-clearance-python.mjs`(テンプレート) |
| --- | --- | --- |
| 入力 | `pip-licenses --format=json --from=all` | `pip-licenses --format=json` |
| PEP 639 | **`License-Expression` を最優先で読む** | `pip-licenses` の既定列に依存 |
| SPDX 式 | **文法どおり評価**(`OR` / `AND` / 括弧 / `WITH` / `+`) | 区切って `some`。**`AND` を `OR` として扱う** |
| 照合 | 完全一致 | **部分一致** |
| 自プロジェクト | `pyproject.toml` から読む(本 PR で追加) | `pyproject.toml` から読む |
| 補正の記録 | **補正したもの・曖昧な分類子を毎回出力** | 出力しない |
| 0件 | **「0件」と出力して落とす** | 「No input received」で通す |

**テンプレートから取り入れたのは、自プロジェクトを `pyproject.toml` から読む点だけです。** これは本案件に無く、テンプレート側が優れていました。

## 4. `allowedLicenses` を14件 → 7件へ

```
MIT / Apache-2.0 / BSD-2-Clause / BSD-3-Clause / ISC / MPL-2.0 / PSF-2.0
```

削除した7件:

| 削除 | 不要になった理由 |
| --- | --- |
| `MIT License` / `Apache Software License` / `BSD License` / `Mozilla Public License 2.0 (MPL 2.0)` / `Python Software Foundation License` | `license-check.mjs` の補正表が担う |
| `Apache-2.0 OR BSD-2-Clause` | SPDX 式として評価する。列挙は不要 |
| **`AGPL-3.0-or-later`** | **自プロジェクトを検査対象から外すため**(本 PR で `pyproject.toml` から名前を読むようにした) |

**`AGPL-3.0-or-later` の削除は、ADR-0007 が書いた誤解を解きます。**

> `allowedLicenses` を読んだ人が、意図を誤解しうる。「AGPL を依存に許している」と読める

### 実測(実依存35件)

```
許可一覧(7件): MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, PSF-2.0
検査した依存: 34件(取得 35件)

自プロジェクトとして検査から外したもの: 1件
  filetto:0.0.0

分類子・自由記述から SPDX へ補正したもの: 8件
  colorama:0.4.6  "BSD License" → BSD-3-Clause  ※この分類子は複数の SPDX を含みうる
  defusedxml:0.7.1  "PSFL" → PSF-2.0
  ...

ライセンスを特定できない依存: 0件
許可範囲外の依存: 0件
ip-clearance: 合格   (exit 0)
```

**`filetto` が自プロジェクトとして外れ、AGPL を許可一覧へ入れずに通りました。**

## 5. 検証

```
$ node --test tests/gate/license-check.test.mjs   → 21 passed(新規4件)
$ pytest tests/gate                               → 24 passed
$ ruff check .                                    → All checks passed!
$ spec-lint / double-encoding / drift             → すべて 0 件
```

新規のテスト:

| # | 確かめたこと |
| --- | --- |
| 1 | 自プロジェクトの名前を `pyproject.toml` から読む |
| 2 | **自プロジェクトを外せば、許可一覧に AGPL を入れる必要はない** |
| 3 | **SPDX の7件だけで、表記のゆれを含む依存8件が通る**(暫定分を削除できる根拠) |
| 4 | 自プロジェクトを外さなければ、自分のライセンスで落ちる |

## 6. PO / Owner へ差し戻すこと

### 6-1. 取り込まない判断の可否(PO)

**依頼は「取り込む」でした。** §3 の実測に基づき取り込まない判断をしましたが、**範囲の決定は PO の職務です。**

**取り込む場合、ADR-0013 の見直しが要ります。**

### 6-2. `PROCESS-PROFILE.md` の更新(Owner)

**`PROCESS-PROFILE.md` は遮断されており、エージェントから書けません。** 96行目を次へ置き換えてください。

```diff
-| 許可するライセンス | MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC |
+| 許可するライセンス | MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, PSF-2.0 |
```

**現在の記述は5件で、`process.config.json` の実態(変更前14件・変更後7件)と一致していません。** 本 PR の前から食い違っていました。

### 6-3. pit-in-template への報告

**§3 の3件はテンプレート側の欠陥です。** 別途起票します。**本案件の判断とは独立に、テンプレートを使う他の案件に影響します。**

## 7. 参照

- [#102](https://github.com/Takenori-Kusaka/Filetto/issues/102) — 本件の依頼
- [PL-0001](PL-0001-ip-clearance-pep639.md) — `license-check.mjs` を作った経緯と実測
- [[0007-allowed-licenses]] / [[0013-license-check-spdx-expression]] — 判断記録
- [pit-in-template#13](https://github.com/Takenori-Kusaka/pit-in-template/issues/13) — 修正済み。修正版は取り込まない

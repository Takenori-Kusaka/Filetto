# PL-0001: ip-clearance を PEP 639 対応へ置き換える(調査と変更案)

対象 Issue: [#60](https://github.com/Takenori-Kusaka/Filetto/issues/60)
作成: 2026-08-13 / レーン: Platform
状態: **適用済み**(強制層の2ファイルは人の操作で配置。手順は [README](README.md))

Platform は検査の装置だけを直します。ADR-0007 の改訂と `process.config.json` の内容判断は PO / 文脈オーナーの領域です。

---

## 1. 結論

| # | 依頼 | 結果 |
| --- | --- | --- |
| 1 | `ip-clearance` が `license_expression` を読むようにする | **pip-licenses 5.5.5 は既に読んでいます。** 読む場所は問題ではありませんでした |
| 2 | classifier が無く `license_expression` がある場合に `UNKNOWN` としないこと | **既に `UNKNOWN` になりません**(実測。§2.1) |
| 3 | PyJWT と `cryptography` で検査が通ることを確認する | **現行構成では `cryptography` が落ちます。** 原因は classifier の欠落ではなく **SPDX 複合式の照合**です(§2.2) |
| 4 | ADR-0007 の暫定部分を削除できるかを PO へ差し戻す | **削除できます。** ただし曖昧さは消えず、置き場所が変わります(§5) |

**Issue #60 の前提は一部当たっていて、一部外れていました。**

- 外れ: 「classifier のみを読むため `UNKNOWN` になる」——`pip-licenses>=5`(本リポジトリの pin)は `License-Expression` を優先して読みます
- **当たり: 「表記の揺れを吸収する回避策では拾えない」**——ただし理由は別で、**`--allow-only` が SPDX 式を文字列として比較するから**です

**結論としての方向は #60 と同じです。** 一覧に文字列を足し続ける回避策は成立しません。読む場所ではなく、**照合の仕方**を変えます。

---

## 2. 実測

再現手順は §6 にあります。すべて実行して得た出力です。

### 2.1 PyJWT / cryptography のメタデータ

`pip-licenses 5.5.5 --format=json --from=all`:

| パッケージ | License-Expression | License-Metadata | License-Classifier |
| --- | --- | --- | --- |
| PyJWT 2.13.0 | `MIT` | UNKNOWN | **UNKNOWN** |
| cryptography 50.0.0 | `Apache-2.0 OR BSD-3-Clause` | UNKNOWN | **UNKNOWN** |

**classifier は確かに消えています。** #60 の指摘どおり PEP 639 移行済みです。
**しかし `--from=classifier` を明示しても pip-licenses は `MIT` を返します。** 5.x は `License-Expression` を先に読みます。「`UNKNOWN` 判定になる」ことは起きませんでした。

### 2.2 現行の `--allow-only` での判定

`adapters/python.json` の現行コマンド + `process.config.json` の現行 `allowedLicenses`(14件):

```
license Apache-2.0 OR BSD-3-Clause not in allow-only licenses was found for package cryptography:50.0.0
exit=1
```

- **PyJWT は通ります**(`MIT` が一覧にある)
- **`cryptography` は落ちます。** `Apache-2.0` も `BSD-3-Clause` も一覧にあるにもかかわらず、**式全体を1つの文字列として比較する**ため不一致になります

現行 `allowedLicenses` に `Apache-2.0 OR BSD-2-Clause` という文字列が入っているのは、同じ問題を `packaging` で踏んだ痕跡です(ADR-0007 §表記の吸収)。**式の組み合わせは無限にあり、列挙では追いつきません。**

### 2.3 `--partial-match` は採れない

pip-licenses には `--partial-match` があり、これを付けると `cryptography` は通ります。**しかし同時に別のものを通します。**

許可一覧を SPDX 8件(`MIT` を含み `MIT-0` を含まない)にして全依存を検査:

| 条件 | 結果 |
| --- | --- |
| `--partial-match` なし | `license MIT-0 not in allow-only ... cffi:2.1.1` → **exit=1(正しい)** |
| `--partial-match` あり | **exit=0** |

**`cffi` の `MIT-0` が、許可していないのに通りました。** 許可一覧の `MIT` が `MIT-0` の部分文字列だからです。
検査の原則2(黙って通る検査を作らない)に反するため、この選択肢は採りません。

### 2.4 本リポジトリの dev 依存 35件のメタデータ分布

| 読めた場所 | 件数 | 例 |
| --- | --- | --- |
| `License-Expression`(PEP 639) | 15 | pytest, ruff, urllib3, packaging(`Apache-2.0 OR BSD-2-Clause`), filetto(`AGPL-3.0-or-later`) |
| `License-Metadata` のみ | 8 | coverage(`Apache-2.0`), certifi(`MPL-2.0`), defusedxml(**`PSFL`**), sortedcontainers(**`Apache 2.0`**) |
| `License-Classifier` のみ | 6 | colorama(`BSD License`), pip_audit(`Apache Software License`), mdurl(`MIT License`) |
| 特定できない | 0 | — |

**3つの場所すべてを読む必要があります。** `License-Expression` だけでは 14件が特定できなくなります。
また `PSFL` `Apache 2.0` のように、**メタデータ側にも SPDX でない自由記述が入ります。**

---

## 3. 変更案

### 3.1 新規: `scripts/gate/license-check.mjs`(強制層)

判定を pip-licenses の文字列比較から引き取ります。

| # | 内容 |
| --- | --- |
| 1 | 読む順序を `License-Expression` → `License-Metadata` → `License-Classifier` とする(PEP 639 に従う) |
| 2 | **SPDX 式を評価する。** `OR` はいずれか許可、`AND` はすべて許可、括弧と `WITH` と `+` を解釈する |
| 3 | 分類子・自由記述を SPDX へ補正する表を持つ(`MIT License` → `MIT` 等) |
| 4 | **補正して通したものを必ず一覧で出力する。** 複数の SPDX を含みうる分類子には印を付ける |
| 5 | **0件のときも「0件」と出力する**(検査の原則2) |
| 6 | ライセンスを特定できない依存があれば落とす。許可一覧が空なら落とす。壊れた SPDX 式も落とす |
| 7 | `PIT_IN_SELF_PACKAGES` で自プロジェクトを検査から外せる。**既定は空**(現行の挙動と同じ)。有効化は検査範囲の変更にあたるため PO の判断 |

判定の本体(`check` / `resolveLicense` / `evaluateExpression`)は入出力を持たない関数として公開し、テストから直接呼べるようにしています。

### 3.3 新規: `tests/gate/`(強制層ではない)

**検査の装置そのものを検査します。**

| ファイル | 役割 |
| --- | --- |
| `tests/gate/license-check.test.mjs` | 判定の単体テスト18件。`node --test` で走る |
| `tests/gate/test_license_check.py` | **CI の `test` 工程(pytest)から上記を起動する橋渡し。** これが無いと、テストが存在するのに一度も実行されない |

`.github/workflows/**` は強制層のため触れません。**pytest から Node を起動することで、ワークフローを変えずに CI へ引き込みます。**
`scripts/gate/license-check.mjs` が存在しない場合、この pytest は失敗します(未適用のまま通る経路を作らないため)。

### 3.2 変更: `adapters/python.json`(強制層)

```diff
-    "licenses": "pip-licenses --format=json --allow-only=\"$PIT_IN_ALLOWED_LICENSES\"",
+    "licenses": "pip-licenses --format=json --from=all | node scripts/gate/license-check.mjs",
```

`PIT_IN_ALLOWED_LICENSES` は `scripts/gate/adapter.mjs` が既に環境変数として渡しているため、そちらの変更は要りません。

### 3.4 触らないもの

| 対象 | 理由 |
| --- | --- |
| `.github/workflows/gate-g5.yml` | `node scripts/gate/adapter.mjs run licenses` のまま。証跡の生成経路も変わりません |
| `process.config.json` | **PO の判断**(§5)。本変更は現行の14件のままでも通ります |
| `context/decisions/0007-allowed-licenses.md` | ADR の改訂は PO / 文脈オーナーの領域 |
| カバレッジ閾値・静的解析の重大度・除外設定 | 本件の対象外 |

---

## 4. 検証

実際に動かした結果です。

### 検証0: 単体テスト18件

```
$ node --test tests/gate/license-check.test.mjs
# tests 18
# pass 18
# fail 0
```

読む順序 / SPDX 式(`OR` `AND` 結合順序 `()` `WITH` `+`)/ 補正表 / 曖昧な分類子の印 /
部分一致で通さないこと / 壊れた式を落とすこと / 特定できない依存を落とすこと / 自プロジェクト除外を網羅しています。

pytest 橋渡しの否定確認: `scripts/gate/license-check.mjs` を退避すると 2件とも失敗しました。**未適用のまま通りません。**

### 検証1: 本リポジトリの dev 依存 35件 / 許可一覧を SPDX 8件のみに絞る

```
許可一覧(8件): MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, PSF-2.0, AGPL-3.0-or-later
検査した依存: 35件(取得 35件)

自プロジェクトとして検査から外したもの: 0件

分類子・自由記述から SPDX へ補正したもの: 8件
  colorama:0.4.6  "BSD License" → BSD-3-Clause  (License-Classifier)  ※この分類子は複数の SPDX を含みうる
  defusedxml:0.7.1  "PSFL" → PSF-2.0  (License-Metadata)
  markdown-it-py:4.2.0  "MIT License" → MIT  (License-Classifier)
  mdurl:0.1.2  "MIT License" → MIT  (License-Classifier)
  pip-api:0.0.34  "Apache Software License" → Apache-2.0  (License-Classifier)  ※この分類子は複数の SPDX を含みうる
  pip_audit:2.10.1  "Apache Software License" → Apache-2.0  (License-Classifier)  ※この分類子は複数の SPDX を含みうる
  sortedcontainers:2.4.0  "Apache 2.0" → Apache-2.0  (License-Metadata)
  tomli_w:1.2.0  "MIT License" → MIT  (License-Classifier)

ライセンスを特定できない依存: 0件
許可範囲外の依存: 0件
ip-clearance: 合格   (exit=0)
```

**表記の吸収6件を削除した許可一覧で通りました。** そして**何を補正したかが出力に残ります。**

### 検証2: PyJWT / cryptography(#60 の発見の元)

```
検査した依存: 2件
分類子・自由記述から補正したもの: 0件
ライセンスを特定できない依存: 0件
許可範囲外の依存: 0件
ip-clearance: 合格   (exit=0)
```

**依頼3を満たしました。** `Apache-2.0 OR BSD-3-Clause` が式として評価され、通ります。

### 検証3(否定): 許可していないものが落ちること

```
許可範囲外の依存: 1件
  cffi:2.1.1  MIT-0  (License-Expression)  許可一覧にありません   (exit=1)
```

**`--partial-match` が通してしまった `MIT-0` を、この実装は落とします。**

### 検証4(否定): SPDX 式の評価

| 式 | 期待 | 結果 |
| --- | --- | --- |
| `Apache-2.0 OR BSD-3-Clause` | 通す | 通した |
| `GPL-3.0-only OR MIT` | 通す(利用者が MIT を選べる) | 通した |
| `MIT AND Apache-2.0` | 通す | 通した |
| **`MIT AND GPL-3.0-only`** | **落とす** | **落とした** |
| `(MIT AND GPL-3.0-only) OR Apache-2.0` | 通す | 通した |
| `GPL-3.0-only AND LGPL-3.0-only OR MIT` | 通す(AND が OR より強く結合) | 通した |
| **`GPL-2.0-only WITH Classpath-exception-2.0`** | **落とす** | **落とした** |
| メタデータ3箇所すべて UNKNOWN | **落とす** | **落とした**(特定できない依存として計上) |

---

## 5. PO への差し戻し(依頼4)

**ADR-0007 の「表記の吸収(暫定)」6件は削除できます。** 検証1がその証拠です。

削除できる項目:

```
MIT License / Apache Software License / BSD License / Apache-2.0 OR BSD-2-Clause /
Mozilla Public License 2.0 (MPL 2.0) / Python Software Foundation License
```

**ただし、曖昧さが消えるわけではありません。** 判断していただきたいのはここです。

| 項目 | 現在(ADR-0007) | 変更後 |
| --- | --- | --- |
| `Apache Software License` の曖昧さ | `process.config.json` の一覧に文字列として存在。**通っても記録に残らない** | `license-check.mjs` の補正表に存在。**通るたびに出力へ「※複数の SPDX を含みうる」と記録される** |
| `BSD License` の曖昧さ | 同上 | 同上 |
| SPDX 式 | 見つけるたびに文字列を追加する | 式として評価する。追加不要 |

**ADR-0007 §非機能への影響「運用」に書かれた懸念——`Apache Software License` が Apache-2.0 以外を指しうる——は残ります。** 変わるのは、**それが黙って通るか、出力に現れるか**です。

PO へお願いしたい判断:

1. 上記6件を `process.config.json` から削除してよいか
2. `AGPL-3.0-or-later`(自プロジェクト自身)の扱い。**既定の挙動は変えていません。** ADR-0007 が「依存に AGPL を許す意図ではない」と書いたとおりで、`filetto` 自身を検査対象から外す方が意図に近いため、`PIT_IN_SELF_PACKAGES` という入口だけ用意して**空のままにしてあります**。有効化は検査範囲の判断です
3. ADR-0007 の改訂範囲。「期限」節(pit-in-template#13 待ち)は、本変更で **#13 を待たずに解消**します

pit-in-template#13 の起票内容(pip-licenses 側での正規化)は引き続き有効です。**本変更はこのリポジトリ側で判定を持つ選択であり、上流の修正を不要にするものではありません。**

---

## 6. 再現手順

```bash
python -m venv venv && venv/bin/pip install -e ".[dev]"
# 2.1 / 2.2
venv/bin/pip install PyJWT cryptography
venv/bin/pip-licenses --format=json --from=all --packages PyJWT cryptography
venv/bin/pip-licenses --format=json \
  --allow-only="$(node -e 'console.log(require("./process.config.json").ci.allowedLicenses.join(";"))')" \
  --packages PyJWT cryptography

# 4 検証0(単体テスト)
node --test tests/gate/license-check.test.mjs
venv/bin/pytest tests/gate/test_license_check.py

# 4 検証1〜3
export PIT_IN_ALLOWED_LICENSES='MIT;Apache-2.0;BSD-2-Clause;BSD-3-Clause;ISC;MPL-2.0;PSF-2.0;AGPL-3.0-or-later'
venv/bin/pip-licenses --format=json --from=all | node scripts/gate/license-check.mjs
```

測定環境: Python 3.14.6 / pip 26.1.2 / pip-licenses 5.5.5 / Windows 11。

---

## 7. 参照

- [#60](https://github.com/Takenori-Kusaka/Filetto/issues/60) — 本件の依頼
- `context/decisions/0007-allowed-licenses.md` — 暫定回避策の判断記録
- `context/projects/P-001.md` 運用上の注意2 — 確認期日 2026-11-12
- [pit-in-template#13](https://github.com/Takenori-Kusaka/pit-in-template/issues/13) — 上流での正規化
- PEP 639 — `License-Expression` メタデータと `License ::` 分類子の非推奨
- SPDX Specification Annex D — 式の文法と `AND` / `OR` の結合順序

---
id: S0-014
stage: S0 探索(S1 の途中で生じた技術検証)
issue: "#146"
status: 実測済み
verdict: 5経路のうち3経路で位置が取れる。.docx はページ番号と座標を持たない。.doc は位置に相当する情報が無い
date: 2026-08-14
---

# S0-014 抽出の工程が原本内の位置を返せるかの実測

Issue [#146](https://github.com/Takenori-Kusaka/Filetto/issues/146) の検証記録です。**5経路すべてを実際に動かしました。ドキュメントの読解で代替した経路はありません。**

**F-003 基準35〜39(確かめる箇所への到達)が成立するかは、抽出の工程が原本内の位置を返せるかに依存します。** 本記録はその可否だけを測ります。**受入基準の書き直しは行いません。**

## 結論

| # | 経路 | 位置が取れるか | 取れる値 |
| --- | --- | --- | --- |
| **1** | **ExStruct `light`**(`.xlsx`) | **取れる** | **シート名 + 行番号 `r` + 列番号 `c`。線形化の前の JSON に入っている** |
| **2a** | **Docling**(`.pptx`) | **取れる** | **スライド番号 `page_no` + 矩形 `bbox` + 文字範囲 `charspan`** |
| **2b** | **Docling**(`.docx`) | **取れない** | **`prov` が全項目で空。`pages` も空。** 本文の通し番号(`#/texts/N`)だけがある |
| **3** | **Docling + RapidOCR**(`.pdf` / 画像) | **取れる** | **ページ番号 `page_no` + 矩形 `bbox` + 文字範囲 `charspan`** |
| **4** | **xlrd**(`.xls`) | **取れる** | **シート名 + 行番号 + 列番号** |
| **5** | **olefile**(`.doc`) | **取れない** | **ストリームの一覧と大きさのみ。段落・ページ・文字位置を表す API が無い** |

**Issue #146 の「結果によって何が変わるか」の表に照らすと、該当するのは「一部で取れない」です。**

**`.xlsx` は線形化の前に取れます。** F-002 基準8(線形化)の設計変更を要する事象は起きていません。

## 測定環境

| 項目 | 値 |
| --- | --- |
| OS | Windows 11 Pro 10.0.26200 |
| Python | 3.12 |
| 主要バージョン | docling 2.119.0 / rapidocr 3.9.2 / onnxruntime 1.28.0 / torch 2.13.0 / exstruct 0.8.1 / xlrd 2.0.2 / olefile 0.47 |
| コーパス | `docs/spikes/assets/corpus`(S0-002 以降と同一) |
| 測定スクリプト | [`S0-014-scripts/`](./S0-014-scripts/) |

**Windows で動かすために環境変数を2つ設定しています。** どちらもコードの変更ではありません。

| 環境変数 | 設定しないと起きたこと |
| --- | --- |
| `PYTHONUTF8=1` | `RuntimeError: Failed to load model ... 'cp932' codec can't decode byte 0x94` でレイアウトモデルの読み込みが失敗 |
| `TORCHDYNAMO_DISABLE=1` | `InvalidCxxCompiler: Compiler: cl is not found` で PDF の変換が失敗(torch.compile が MSVC を要求する) |

**実装時に同じ設定が要ります。** 設定しない場合、**Windows では PDF の抽出が動きません。**

## 経路1: ExStruct `light`(`.xlsx`)

**線形化の前の JSON に、シート名と行・列の番号が入っています。**

`kakei-06.xlsx` の出力の先頭:

```json
{
  "book_name": "kakei-06.xlsx",
  "sheets": {
    "表２": {
      "rows": [
        { "r": 1, "c": { "2": "2026 年 ６ 月 分" } },
        { "r": 2, "c": { "1": "項      目　　", "12": "二人以上の世帯" } },
        { "r": 3, "c": { "17": "うち勤労者世帯", "21": "うち無職世帯" } }
```

**構造は `sheets[シート名].rows[].r` と `.c[列番号]` です。** 値そのものが列番号をキーに持つため、**テキストと座標が1対1で対応します。**

実測値:

| ファイル | 所要 | シート | 値のある行 | 値のあるセル | 出力 |
| --- | --- | --- | --- | --- | --- |
| `kakei-05.xlsx` | 2.39s | `表１` | 100 | **2,604** | 75,668 B |
| `kakei-06.xlsx` | 2.29s | `表２` | 219 | **1,925** | 75,578 B |
| `kochi-02.xlsx` | 1.98s | `様式` | 14 | 19 | — |

**行オブジェクトのキーは `["c", "r"]` の2つだけです。** 位置を表す欄が後付けの拡張ではなく、出力構造の一部であることを意味します。

## 経路2: Docling(`.docx` / `.pptx`)

**同じライブラリでも、形式によって結果が分かれました。**

### `.pptx` は取れます

`chisou-01.pptx`(32スライド):

| 項目 | 値 |
| --- | --- |
| 所要 | 0.32s |
| 項目数 | **434** |
| **位置(`prov`)を持つ項目** | **434(全件)** |
| `pages` に現れたスライド番号 | 1〜32 |

出力の実物:

```json
{
  "self_ref": "#/texts/1",
  "label": "title",
  "prov": [{
    "page_no": 1,
    "bbox": {"l": 681038.0, "t": 3509963.0, "r": 9224963.0, "b": 1122363.0,
             "coord_origin": "BOTTOMLEFT"},
    "charspan": [0, 9]
  }],
  "text": "【計画のタイトル】"
}
```

**`page_no` がスライド番号、`bbox` が矩形、`charspan` が項目内の文字範囲です。**

### `.docx` は取れません

**3ファイルで測り、いずれも `prov` が全項目で空でした。**

| ファイル | texts | tables | **`prov` を持つ項目** | `pages` |
| --- | --- | --- | --- | --- |
| `inashiki-06.docx` | 68 | 0 | **0** | `{}`(空) |
| `kochi-01.docx` | 29 | 1 | **0** | `{}`(空) |
| `kochi-06.docx` | 166 | 0 | **0** | `{}`(空) |

出力の実物(`inashiki-06.docx` の `#/texts/2`):

```json
{
  "self_ref": "#/texts/2",
  "parent": {"$ref": "#/body"},
  "children": [],
  "content_layer": "body",
  "label": "text",
  "prov": [],
  "orig": "仲　　裁　　合　　意　　書",
  "formatting": {"bold": true, "italic": false, "underline": false,
                 "strikethrough": false, "script": "baseline"}
}
```

**`prov` は欄としては存在しますが、空の配列です。** ページ番号も座標もありません。

**取れるのは通し番号だけです。** `self_ref` が `#/texts/0` から連番で振られ、`body.children` が読み順の参照列を持ちます。

```json
"body": {"children": [{"$ref": "#/texts/0"}, {"$ref": "#/texts/1"}, {"$ref": "#/texts/2"}]}
```

**`kochi-01.docx` では表が本文の途中に現れ、`children` が `#/texts/0` → `#/tables/0` → `#/texts/1` の順を保持していました。** **本文中の順序は取れます。ページ上の位置は取れません。**

**回避策は探していません**(Issue #146 の測り方3)。`.docx` に対して LibreOffice を介す経路の警告が出ましたが、**それは別の依存を増やす選択であり、本記録の対象外です。**

```
Found DrawingML elements in document, but no DOCX to PDF converters.
If you want these exported, make sure you have LibreOffice binary in PATH
```

## 経路3: Docling + RapidOCR(`.pdf` / 画像)

**`force_full_page_ocr=True` を有効にして測りました**(F-002 基準7 の指定と同じ)。

| ファイル | 所要 | 項目数 | **`prov` を持つ項目** | ページ |
| --- | --- | --- | --- | --- |
| `kakei-02.pdf`(24ページ) | **252.44s** | 904 | **904(全件)** | 1〜24 |
| `fig-kakei-02.png` | 3.06s | 46 | **46(全件)** | 1 |

出力の実物(`kakei-02.pdf` の先頭):

```json
{
  "self_ref": "#/texts/0",
  "label": "section_header",
  "prov": [{
    "page_no": 1,
    "bbox": {"l": 118.81296793619792, "t": 720.6229858398438,
             "r": 484.1311442057292, "b": 685.398183186849,
             "coord_origin": "BOTTOMLEFT"},
    "charspan": [0, 12]
  }],
  "text": "家計調査報告（家計収支編"
}
```

**画像でも同じ形です。** `fig-kakei-02.png` は文字レイヤを持たない画像であり、**46項目すべてが OCR の結果です。それらにも `bbox` が付きました。**

### RapidOCR を直接呼ぶ経路(F-002 基準7-2)

**こちらでも座標が取れます。** `fig-kakei-02.png` を直接渡した結果:

| 項目 | 値 |
| --- | --- |
| 所要 | 1.87s |
| 検出した領域 | **44** |
| 返る欄 | `boxes` / `txts` / `scores` |

```
boxes[0] = [[451.0, 41.0], [1233.0, 41.0], [1233.0, 114.0], [451.0, 114.0]]
txts[0]  = "家計調査結果の最近の動向"
scores[0]= 0.99813
```

**Docling 経由の矩形は4値(`l/t/r/b`)、RapidOCR 直接は4点の多角形です。** **F-002 基準7-2 が「文字数が多いほうを採用する」と定めているため、採用した経路によって座標の形が変わります。**

## `.doc` は位置に相当する情報を持ちません

**olefile が返すのは OLE 複合ドキュメントのストリームの一覧と大きさだけです。**

`inashiki-07.doc`:

```json
{
  "streams": ["CompObj", "Ole", "DocumentSummaryInformation",
              "SummaryInformation", "1Table", "WordDocument"],
  "stream_sizes": {"WordDocument": 4658, "1Table": 1891, "SummaryInformation": 344}
}
```

`inashiki-09.doc` も同じ6ストリームで、大きさだけが異なりました(`WordDocument`: 8,242)。

**段落・ページ・文字位置を表す API は olefile に存在しません。** **これは Issue #146 が「取れないという前提の確認」として挙げた経路であり、確認できました。**

**`.doc` については、S0-003 が既に「罫線レイアウトの復元はできない」と測っており、`specs/F-002/spec.md` のスコープ外にも明記されています。** 本記録はそれと矛盾しません。

## 経路4: xlrd(`.xls`)

**シート名・行番号・列番号がそのまま取れます。**

| ファイル | シート名 | 行 | 列 | 文字列セル |
| --- | --- | --- | --- | --- |
| `inashiki-01.xls` | `入札（見積）書` | 45 | 30 | 22 |
| `inashiki-08.xls` | `工程表` | 38 | 78 | 66 |

出力の実物:

```json
{"sheet": "入札（見積）書", "row": 0, "col": 0, "text": "様式第１０号（第１７条第１項関係）"}
{"sheet": "入札（見積）書", "row": 3, "col": 0, "text": "入札書"}
{"sheet": "入札（見積）書", "row": 8, "col": 25, "text": "年"}
```

**`.xlsx`(経路1)と同じ粒度です。** シート名 + 行 + 列で1つのセルを指せます。

## 位置の表し方が経路ごとに異なります

**F-003 基準37 は「安定 ID と原文内の位置(ページ番号または先頭からの文字数)の組」で表すことを求めています。** **実測で得られた位置は、この2種類に収まりません。**

| 経路 | 得られた位置 | 基準37 の2種類に収まるか |
| --- | --- | --- |
| `.xlsx` / `.xls` | **シート名 + 行 + 列** | **収まらない。** ページ番号でも文字数でもない |
| `.pptx` | スライド番号 + 矩形 + 文字範囲 | ページ番号として扱える |
| `.pdf` / 画像 | ページ番号 + 矩形 + 文字範囲 | 収まる |
| `.docx` | **本文中の通し番号のみ** | **収まらない** |
| `.doc` | なし | — |

**これは実測から出た事実であり、判断ではありません。** **基準37 の書き方をどうするかは PO の領域です。**

## この記録で判定していないこと

| # | 判定していないこと |
| --- | --- |
| 1 | **F-002 の受入基準に何をどう追加するか。** 受入基準の変更は G-2 の再判定を要します |
| 2 | **`.docx` と `.doc` を、位置が出ない経路として扱うかどうか。** F-003 基準38(位置を特定できないことを明示する)で受け止めるかの判断 |
| 3 | **基準37 の位置の表し方**(上記のとおり実測が2種類に収まりません) |
| 4 | **座標を派生物として保存するかどうか。** 保存量が増えます。`kakei-02.pdf` は904項目すべてが矩形を持ちます |
| 5 | **252秒という PDF の所要時間を受け入れるかどうか。** S0-003 の初回構築の見積(50ファイルで約25分)と整合するかは測っていません |

## 再現の手順

```bash
python -m venv s0014
./s0014/Scripts/python -m pip install docling rapidocr onnxruntime exstruct xlrd olefile openpyxl

# 経路1
./s0014/Scripts/python probe_exstruct.py ./s0014/Scripts/exstruct.exe <corpus> kakei-05.xlsx kakei-06.xlsx kochi-02.xlsx
# 経路2
PYTHONUTF8=1 ./s0014/Scripts/python probe_docling.py <corpus> inashiki-06.docx chisou-01.pptx
# 経路3
PYTHONUTF8=1 TORCHDYNAMO_DISABLE=1 ./s0014/Scripts/python probe_pdf.py <corpus> kakei-02.pdf fig-kakei-02.png
# 経路4・5
PYTHONUTF8=1 ./s0014/Scripts/python probe_legacy.py <corpus> inashiki-01.xls inashiki-08.xls inashiki-07.doc inashiki-09.doc
```

**出力の実物は [`S0-014-scripts/`](./S0-014-scripts/) の4つの JSON にあります。**

## 関連

- [#146](https://github.com/Takenori-Kusaka/Filetto/issues/146) — 本記録の起票元
- `specs/F-003/spec.md` 基準35〜40 / 前提5 — 本記録が前提の可否を測った対象
- `specs/F-002/spec.md` 基準7・7-2・8・9・10 — 測った5経路の出所
- [S0-003](./S0-003-parser-and-hybrid.md) — パーサの選定。`.doc` の限界を先に測っている
- [S0-006](./S0-006-ocr-glyph.md) — OCR の字形。同じコーパスを使用

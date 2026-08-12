---
id: S0-001
stage: S0 探索
issue: "#1"
status: 判定済み
verdict: 前提は成立しない
date: 2026-08-12
---

# S0-001 Graphify が汎用ドキュメント(日本語 PDF / Office)で実用精度を出せるか

Issue #1 の検証記録です。実作業は 1 日の時間箱内(約 1 時間)で完了しました。

## 結論

**前提は成立しません。**

企画が立脚していた「Graphify によるナレッジグラフ構築だけで、外部 API・ベクトル DB なしに実用的なセマンティック検索を成立させる」という前提は、実データで否定されました。理由は 2 つあり、いずれも回避策のない構造的なものです。

1. **外部 API なしでは、コード以外のファイルは 1 件も取り込めない。** 「維持コストゼロ」の訴求はこの時点で成立しません(基準4 不合格)。
2. **API を使って取り込めた場合でも、日本語自然文クエリの正答率は最良で 3/10。** 要求水準の 7/10 に遠く届きません(基準2 不合格)。

基準1(取り込み)と基準3(所要時間)は満たせますが、この 2 つを満たしても製品にはなりません。

## 実行環境

| 項目 | 値 |
| --- | --- |
| OS | Windows 11 Pro 10.0.26200 |
| Python | 3.12.11(検証用 venv) |
| Graphify | graphifyy 0.9.40(`graphify` コマンド) |
| 追加導入した extras | `[office]` `[pdf]` `[anthropic]` `[chinese]` |
| 主要依存 | pypdf 6.15.0 / python-docx 1.2.0 / openpyxl 3.1.5 / anthropic 0.121.0 / jieba 0.42.1 |
| LLM バックエンド | `--backend claude`(既定モデル `claude-sonnet-4-6`) |
| ライセンス | Apache-2.0 / MIT のデュアル |

Issue の手順にあった `pipx install graphify` は誤りでした。PyPI の配布名は **`graphifyy`**(y が 2 つ)です。

## 投入したファイル

**50 ファイル / 16MB。** 合成データではなく、実在する日本の行政・公共サイトから取得した公開ファイルです(総務省統計局、デジタル庁、高知県、大阪市、稲敷市、上三川町、厚生労働省、内閣官房)。日本固有の構造(いわゆる神エクセル、Word で罫線を引いた様式、工事関係の要綱・誓約書)を意図的に含めています。

| 形式 | 件数 | 内容 |
| --- | --- | --- |
| .pdf | 19 | 白書・要綱・統計報告・入札関係の通知。うち 2 件はテキスト層を持たない画像 PDF(スキャン相当) |
| .xlsx | 6 | 家計調査の統計表、県の入札様式(セル結合とふりがな列を多用) |
| .xls | 6 | 市の入札・工事様式(レガシーバイナリ形式) |
| .docx | 5 | 仲裁合意書、誓約書、コンプライアンス基本方針のひな形 |
| .doc | 3 | 市の様式(レガシーバイナリ形式) |
| .pptx | 3 | 厚労省の制度説明スライド、内閣官房の申請様式 |
| .png | 4 | 白書・統計資料から抽出した図表ページの画像 |
| .md | 4 | 日本語のメモ 3 件、英語のドキュメント 1 件 |

スキャン PDF 2 件と図表画像 4 件は、取得した PDF のページを画像化して作成しました(元データは実在の行政文書)。それ以外の 44 件はダウンロードしたそのままです。

## 基準ごとの判定

| # | 基準 | 判定 |
| --- | --- | --- |
| 1 | 日本語のテキスト PDF と .docx が、エラーなく取り込まれる | **条件つき合格**(既定インストールでは不合格) |
| 2 | 日本語クエリ 10 件のうち 7 件以上で期待ファイルが上位 3 件 | **不合格(最良 3/10)** |
| 3 | 50 ファイルのインデックス構築が 10 分以内 | **合格(2 分 11 秒)** |
| 4 | 外部 API キーなしで 1〜3 が成立する | **不合格** |

### 基準1: 取り込み — 条件つき合格

`graphifyy[pdf]` と `graphifyy[office]` を明示的に導入した状態では、日本語のテキスト PDF 17 件と .docx 5 件がすべて取り込まれ、ノードが生成されました。

ただし **既定のインストールでは PDF が 1 件も取り込まれず、しかもエラーが出ません**。原因はコード上で特定しました。

- `graphify/detect.py:529` の `extract_pdf_text()` は `from pypdf import PdfReader` を実行し、失敗を `except Exception: return ""` で握り潰します
- pypdf は `[pdf]` extra にのみ含まれ、`[office]` には含まれません
- 結果、PDF は空文字として LLM に送られます。実際に送信されたメッセージを傍受して確認しました:

```
=== MODEL: claude-sonnet-4-6 max_tokens: 16384 images: 0
=== USER MESSAGE len: 134
<untrusted_source path="attention.pdf" sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855">

</untrusted_source>
```

この sha256 は**空文字列のハッシュ**です。graphify 側はこれを「モデルの応答が不完全(hollow)」と誤認し、チャンクを分割して再試行し、最後に「19/38 files produced no nodes」と報告します。利用者には「LLM がノードを返さなかった」としか見えず、依存が足りていないことは分かりません。

英語の PDF(arXiv:1706.03762)でも同一の症状が再現したため、**これは日本語固有の問題ではなく Graphify 側の欠陥**です。

対応形式そのものにも欠落があります。**50 件中 12 件は拡張子が未対応で、分類すらされずスキップされました**。

```
[graphify extract] 12 file(s) not classified (no supported extension or shebang), skipped:
  chisou-01.pptx, inashiki-01.xls, inashiki-02.xls, inashiki-03.xls, inashiki-04.xls, inashiki-05.xls (+6 more)
```

内訳は **.xls 6 件 / .doc 3 件 / .pptx 3 件**です。python-pptx は `[all]` を含むどの extra にも入っておらず、**.pptx は対応形式ではありません**。日本の行政サイトが配布する様式はレガシーの .xls / .doc が依然として多数を占め、制度説明資料は .pptx が標準です。この 3 形式が未対応であることは、Filetto の想定用途にとって致命的です。

スキャン PDF 2 件はテキスト層がないため 0 ノードでした(仕様どおりの挙動)。OCR は行われません。

最終的にグラフへ入ったのは **50 件中 36 件**、126 ノード / 139 エッジ / 17 コミュニティです。

### 基準2: 検索精度 — 不合格(最良 3/10)

クエリ 10 件はインデックス構築の**前に**確定し、以後変更していません(期待ファイルは本文抽出結果から人が決めました)。判定は「期待ファイルが検索結果の上位 3 件に含まれるか」です。

`[chinese]` extra(jieba)なしの結果:

| # | クエリ | 期待 | 上位3件の出典 | 判定 |
| --- | --- | --- | --- | --- |
| Q1 | 仲裁合意書の様式はどこ | inashiki-06.docx | (該当なし) | 不合格 |
| Q2 | 入札書はどうやって折って提出するのか | kaminokawa-01.pdf | kaminokawa-03 / -02 / **-01** | 合格 |
| Q3 | 消費支出が前年同月比でどれくらい減ったか書いてある資料 | kakei-02/03/04.pdf | **kakei-02** / **kakei-03** / kakei-02 | 合格 |
| Q4 | 障害者を雇用していることを誓約する書類 | kochi-01.docx | (該当なし) | 不合格 |
| Q5 | コンプライアンス基本方針のひな形 | kochi-06/07/08.docx | digital-03 / -02 / -02 | 不合格 |
| Q6 | 電子納品のやり方を定めた要領 | kaminokawa-05.pdf | (該当なし) | 不合格 |
| Q7 | 県外の業者が入札に参加するときの資格審査の要綱 | kochi-04.pdf | kaminokawa-02 / -01 / -03 | 不合格 |
| Q8 | デジタル社会の実現に向けた重点計画 | digital-01.pdf | **digital-01** / -02 / -04 | 合格 |
| Q9 | 介護保険制度の改正について説明したスライド | mhlw-01.pptx | kaminokawa-03 / digital-04 / -04 | 不合格 |
| Q10 | 袋とじの作り方 | kaminokawa-04.pdf | (該当なし) | 不合格 |

**3/10。** Q1 / Q4 / Q6 / Q10 は `No matching nodes found.` で、検索結果が 0 件でした。

原因は検索語の分割にあります。`graphify/serve.py:172` の `_search_tokens()` は `re.findall(r"\w+", ...)` で語を切ります。日本語は語の間に空白がないため、「電子納品のやり方を定めた要領」は 1 つのトークンになり、ノードラベルにその文字列が丸ごと含まれない限り一致しません。Graphify 自身がこの問題を認識しており、中国語向けに jieba 分割の `[chinese]` extra を用意しています。**日本語向けの分割は用意されていません**。

そこで `[chinese]`(jieba)を導入して同じ 10 件を再実行しました。全クエリで「0 件」は解消しましたが、精度は **2/10 に悪化**しました。jieba は中国語の辞書で分割するため、日本語では助詞や活用語尾が独立した高頻度トークンとして残り、無関係なノード(`digital-03.pdf` など)が全クエリの上位に居座ります。実際、Q2〜Q10 のうち 7 件で `digital-03.pdf` が 1 位でした。

| 条件 | 正答数 |
| --- | --- |
| jieba なし | 3/10 |
| jieba あり(`[chinese]`) | 2/10 |

Q9 の期待ファイル mhlw-01.pptx は .pptx が未対応のためインデックスに存在せず、原理的に到達できません。

### 基準3: 所要時間 — 合格

50 ファイル(16MB)のインデックス構築は **2 分 11 秒**(2026-08-12 15:00:17 → 15:02:29)。10 分の上限に対して十分な余裕があります。並列は既定の 4 チャンク同時。

なお 2 回目以降は増分更新が効き、変更なしのファイルはキャッシュから読まれます(19 件キャッシュ / 19 件再抽出のケースで 26 秒)。

### 基準4: 外部 API キーなしで成立するか — 不合格

**成立しません。** Issue で最も厳密に確認するよう指示された基準であり、結果は明確です。

API キーを何も設定しない状態で実行すると、graph.json すら生成されずエラー終了します。

```
error: no LLM API key found (38 doc/paper/image file(s) need semantic extraction).
Set GEMINI_API_KEY or GOOGLE_API_KEY (gemini), MOONSHOT_API_KEY (kimi), ANTHROPIC_API_KEY (claude),
OPENAI_API_KEY (openai), DEEPSEEK_API_KEY (deepseek), or pass --backend.
A code-only corpus needs no key.
```

`--code-only` を付けると鍵なしで動きますが、非コードファイルを全件スキップするため、**このコーパスでは空グラフになります**。

```
[graphify extract] --code-only: skipping 38 non-code file(s) (15 docs, 19 papers, 4 images) — no LLM extraction
[graphify extract] found 0 code, 0 docs, 0 papers, 0 images
[graphify extract] graph is empty — extraction produced no nodes.
```

#### どの機能が外部 API を要求するか

| 機能 | 外部 API |
| --- | --- |
| コードの AST 解析(tree-sitter) | **不要**。完全にローカル |
| 文書・PDF・画像のセマンティック抽出 | **必須**。これが無いとノードが 1 件も生まれない |
| コミュニティの命名(`label` / `cluster-only`) | 必須(`--no-label` で回避可) |
| グラフ探索(`query` / `path` / `explain`) | 不要。生成済み graph.json に対するローカル BFS |

つまり **Graphify のローカル性はコードベースに対するものであり、文書コーパスには適用されません**。Filetto が対象とする「個人の雑多な資料倉庫」は 100% が非コードであり、LLM バックエンドなしでは何も起きません。

唯一の抜け道は Ollama をバックエンドにすることです(ローカル実行・課金なし)。ただしこれは「維持コストゼロ」ではなく「利用者が数 GB のモデルを自機で常時運用する」ことを意味し、企画の訴求とは別物です。今回は検証していません。

#### 実測コスト

今回の検証で発生した API 課金は概算 **約 2.0 USD** です。

| 実行 | トークン | 概算 |
| --- | --- | --- |
| 1 回目(PDF 空のまま) | 159,442 in / 15,419 out | $0.71 |
| 再試行 | 13,950 in / 480 out | $0.05 |
| 本番(pypdf 導入後) | 311,018 in / 19,726 out | $1.23 |

50 ファイルで約 1.2 USD。個人の資料倉庫が数千ファイル規模になれば、初回構築だけで数十 USD の水準です。

## 想定外だった挙動

1. **PyPI の配布名が `graphify` ではなく `graphifyy`。** Issue の手順は実行できません
2. **PDF 対応が別 extra(`[pdf]`)で、未導入時は無言で空になる。** `except Exception: return ""` が原因を隠します
3. **`--backend claude` は `anthropic` パッケージを要求するが、`[anthropic]` extra は自動では入らない。** 未導入だと全チャンクが失敗します
4. **.pptx はどの extra でも対応していない**(python-pptx への依存が存在しない)
5. **jieba を入れると日本語検索がむしろ悪化する**

## この検証で判断していないこと

- Ollama バックエンドでの精度と所要時間(モデル導入が必要なため未実施)
- 数千ファイル規模での挙動(50 ファイルで前提が否定されたため実施せず)
- Graphify 以外の手段(本 spike の範囲外。PO の判断事項)

## 再現手順

```bash
uv venv gfxenv --python 3.12
uv pip install --python gfxenv/Scripts/python.exe "graphifyy[office]" "graphifyy[pdf]" anthropic
export ANTHROPIC_API_KEY=...
gfxenv/Scripts/graphify.exe extract <コーパスのパス> --out out --backend claude
gfxenv/Scripts/graphify.exe query "電子納品のやり方を定めた要領" --graph out/graphify-out/graph.json
```

検証に使ったコーパスの取得元一覧、10 件のクエリ定義、生の実行ログは、レビュー時に提示できる状態で保持しています。

## 関連

- Issue #1
- 案件層コンテキスト: `context/projects/P-001.md` 前提1(本リポジトリには未作成)

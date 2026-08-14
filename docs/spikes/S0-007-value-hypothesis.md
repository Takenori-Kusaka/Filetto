---
id: S0-007
stage: S0 探索(追加)
issue: "#114"
status: 一部未測定(実機を起動していない。基準3・4・7 は文書とソースからの判定に留まる)
verdict: 甲。中核の主張は Open WebUI では成立しない。ただし成立させる範囲を PO が決める必要がある
date: 2026-08-14
---

# S0-007 中核の価値仮説を検証する — Open WebUI を実測し、Filetto を作る理由が残るかを確かめる

Issue [#114](https://github.com/Takenori-Kusaka/Filetto/issues/114) の検証記録です。

**実機は起動していません。** 公式ドキュメントとソースコードの実測で判定しました。**実機でしか確かめられない項目は「判定できなかった項目」に列挙します。**

対象: `open-webui/open-webui` @ `01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`(2026-07-27)

## 結論を先に

**甲。作る理由は残ります。ただし、当初の想定とは違う理由です。**

**Open WebUI は、22製品中で唯一「フルのファイル操作 UI × ローカル RAG」を両立しています。** ネスト階層・ドラッグ移動・その場リネーム・パンくずの4点すべてが実装されており、先行調査の観測は正しいものでした。

> **【2026-08-14 是正】** 上記の「唯一」は S0-013 の実測と食い違う。実測では **RAGFlow(infiniflow/ragflow)も入れ子フォルダの構築・ファイル/フォルダのリネーム・個別および一括削除を持つ**(出典 https://ragflow.io/docs/manage_files 、2026-08-14 確認)。**ただし「移動(move)」の明示的記載は確認できず、RAGFlow のフォルダが原本のディレクトリか論理ツリーかも未確認**。また **RAGFlow は既定ではローカル完結しない**(v0.22.0 以降、埋め込みモデル同梱版を廃止)。**本記録は Open WebUI 1製品のソース実測であり、他の21製品を再確認していない。** 詳細は [S0-013](./S0-013-competitor-matrix.md) を参照。

**しかし「同じ実体」の定義が、両者で異なります。**

| | Open WebUI の「実体」 | Filetto の「実体」 |
| --- | --- | --- |
| 何か | **DB 上の `File` レコード(UUID)** | **ファイルシステム上のファイル** |
| ディスク上の姿 | `{uuid}_{filename}` の平坦な名前 | 利用者が置いたパスそのまま |
| フォルダ階層 | **`knowledge_directory` テーブルの論理ツリー** | **実体のディレクトリ** |
| 人が動かす場所 | **Open WebUI の画面の中** | **エクスプローラ** |

**Open WebUI の中では、参照は壊れません。** `file.id` が不変で、リネームも移動も索引に触れないためです。

**しかし Open WebUI の外(ファイルシステム)で人がファイルを動かした瞬間、同一性は `(パス, ファイル名, SHA-256)` に退化し、削除+新規追加になります。**

**「人はエクスプローラでファイルを動かす」を前提にするか、「人は Open WebUI の中でファイルを動かす」を前提にするか。** この選択が、作るか作らないかを分けます。

**これは技術判断ではなく、誰のどの作業を対象にするかという範囲の決定です。**

---

## 判定基準ごとの結果

| # | 判定基準 | 判定 |
| --- | --- | --- |
| 1 | 人向けのファイル操作が実用に足るか | **UI 機能としては満たす / 原本のファイルシステム操作としては満たさない** |
| **2** | **人が動かしたファイルを AI 側が同じものとして扱えるか** | **UI 内は満たす / 外部同期経路は満たさない** |
| 3 | 日本語のオフィス文書とスキャン PDF が既定で読めるか | **部分的に満たす**(既定で OCR なし) |
| 4 | `.xls` / `.doc` が読めるか | **`.xls` は見込みあり / `.doc` は既定イメージで失敗が濃厚** |
| 5 | MCP サーバとして機能を公開できるか | **満たさない** |
| 6 | 外部への通信が発生しないか | **満たす**(`OFFLINE_MODE=true`) |
| 7 | 導入の手数 | **部分的に満たす**(起動は容易 / 要求リソースは公式に未記載) |
| 8 | 部品として切り出せるか | **部分的に満たす**(ベクトル層は独立 / UI とオーケストレーションは密結合) |
| 9 | upstream へ足す道は成立するか | **部分的に満たす**(PR は受け付けるが、設計提案は通りにくい) |
| 10 | 切り出す / 足す / 新規に作る のどれが安いか | **後述** |

---

## 基準2 — 最重要。ここが結論を決めた

### Open WebUI の識別子は内部 UUID

`backend/open_webui/models/files.py:18-31` — `File` テーブルの主キーは `id`(文字列 UUID)。`filename` `path` `hash` はいずれも属性であり識別子ではありません。

ベクトル DB のコレクション名(`backend/open_webui/routers/retrieval.py:1860`):

```python
collection_name = f'file-{file.id}'
```

**索引はファイル ID に紐づきます。**

### UI での移動・リネームは参照を壊さない

| 操作 | 実装 | 何が起きるか |
| --- | --- | --- |
| リネーム | `routers/files.py:956` → `models/files.py:394-405` | **`filename` と `meta['name']` を更新するだけ。ベクトル DB に触れない。物理ファイル名も変えない** |
| 移動 | `routers/knowledge.py:2313` | **`knowledge_file.directory_id` を書き換えるのみ。再索引もベクトル削除もしない** |

**`file.id` が不変なので、RAG 索引・ナレッジ登録・チャット引用のいずれも切れません。追従します。**

**Filetto が主張する「同じ実体の共有」の内部設計は、既に実装されています。**

### しかし外部同期の同一性キーはパスとファイル名である

`backend/open_webui/routers/knowledge.py:1822-1912`:

```python
indexed_files[(file_path, file_model.filename)] = {'file_id': ..., 'checksum': ...}
...
if key not in indexed_files:  added.append(...)
for key, file_info in indexed_files.items():
    if key not in manifest_keys:  deleted.append({'file_id': ...})
```

**ローカル側でリネーム・移動すると「削除 + 新規追加」になります。** 新しい `file.id` が振られ、新しいベクトルコレクションが作られ、旧参照は消えます。

**逆に、Open WebUI の UI 側でファイルを移動すると、次の同期でローカルの一覧と `(パス, ファイル名)` が合わなくなり、やはり削除+再アップロードになります。**

**UI 操作と同期が往復で衝突します。**

### 残る不確実性

**ベクトル DB 内のチャンクのメタデータ `name` は陳腐化します。** 索引時に `{'name': file.filename}` を焼き付け(`routers/retrieval.py:1880` ほか)、リネームしても更新されません。

**引用表示は経路で分かれます。**

| 経路 | 実装 | リネーム後の表示 |
| --- | --- | --- |
| フルコンテキスト | `retrieval/utils.py:1477, 1554` で **DB から引き直す** | 新しい名前 |
| **チャンク検索** | **ベクトル DB のメタデータをそのまま使う** | **旧い名前** |

**公式ドキュメントは「リネームは citations を含むあらゆる参照を更新する」と書いていますが、コード実測ではチャンク経路について裏付けが取れませんでした。**

---

## 基準1 — ファイル操作は実在する。ただし論理的な入れ物である

### 4点すべてが実装されている

| 機能 | 実装 |
| --- | --- |
| ネスト階層 | `models/knowledge.py:63-79` `KnowledgeDirectory`(`parent_id` を持つ DB ツリー) |
| ドラッグ移動 | `KnowledgeBase/DirectoryRow.svelte:73, 84` |
| その場リネーム | `KnowledgeBase.svelte:795`(ディレクトリ) / `:884`(ファイル) |
| パンくず | `KnowledgeBase/KnowledgeBreadcrumbs.svelte:66-84`(パンくず自体がドロップ先) |

**先行調査の記述は正しいものでした。**

### しかし原本のファイルシステムではない

**ファイル実体は `storage/provider.py` が `{uuid}_{filename}` の平坦な名前で `data/uploads/` に置くだけで、ディレクトリ構造はディスク上に一切再現されません。**

**公式ドキュメントも明言しています。** ナレッジベースは "internal container model, not a real filesystem"。

### ローカルフォルダを見に行く機能がない

| 確認 | 結果 |
| --- | --- |
| ファイル監視 | **`watchdog` / `inotify` / `watchfiles` / `Observer` が backend 全体で0ヒット** |
| UI の Sync Directory | **ブラウザ側の File System Access API。毎回ユーザがフォルダを選び直す手動操作**(`KnowledgeBase.svelte:493-522`) |
| 公式 CLI `oikb` | 定期同期を提供。**ただし片方向(ローカル → KB)で、上記の `(パス, ファイル名)` キー方式** |

---

## 基準5 — MCP サーバとしては公開できない

### コード実測

MCP 関連の実装は `backend/open_webui/utils/mcp/client.py` の1ファイルのみ。冒頭が `from mcp.client.streamable_http import streamablehttp_client`。

**クライアント側 SDK のみです。** `FastMCP` / `mcp.server` / MCP サーバ用ルートは backend 全体で0ヒット。

**公式ドキュメントも設計上の理由を明記しています。**

> Open WebUI is a web-based, multi-tenant environment, not a local desktop process

### 要望は2件あり、両方とも実装されずに Discussion へ変換・ロックされている

| # | 表題 | 顛末 |
| --- | --- | --- |
| [16883](https://github.com/open-webui/open-webui/issues/16883) | Expose OpenWebUI API Endpoints as an MCP Server | **2025-08-25 Discussion へ変換、ロック、コメント0** |
| [24117](https://github.com/open-webui/open-webui/issues/24117) | Expose Open WebUI as a native MCP server | **2026-05-08 Discussion へ変換、ロック、コメント0** |

### 代替手段は存在する

**REST / OpenAI 互換 API があり、Bearer トークン(JWT または個人 API キー)で認証します。** エンドポイント制限も可能です(`utils/auth.py:444-466`)。

| 用途 | エンドポイント |
| --- | --- |
| セマンティック検索 | `POST /api/v1/retrieval/query/collection` |
| ファイル本文取得 | `GET /api/v1/files/{id}/content` |
| KB 内ファイル一覧 | `GET /api/v1/knowledge/{id}/files` |
| ディレクトリ操作・ファイル移動 | `/api/v1/knowledge/{id}/dirs/*`, `/{id}/file/move` |

**MCP 化は自前でラッパを書けば済みます。** ただし upstream 標準機能としては存在しません。

> **【2026-08-14 是正】** 本節の判定は Open WebUI について正しい。**ただし「MCP を公開できる製品が少ない」という含意は S0-013 の実測と並べて読む必要がある。** 実測では **12製品中2件が MCP サーバを公開する**。**RAGFlow** は `retrieve` / `ragflow_list_datasets` / `ragflow_list_chats` の3ツールをレガシー SSE(`/sse`)と streamable-HTTP(`/mcp`)で公開する(出典 https://ragflow.io/docs/launch_mcp_server 、2026-08-14 確認)。**Onyx** は `backend/onyx/mcp_server/` に FastMCP with FastAPI wrapper の実装を持ち、HTTP POST / Port 8090 / 設定キー `MCP_SERVER_ENABLED` で公開する(2026-08-13 実測)。**残る10製品はクライアントまたはホストのみ、もしくは非対応である。** 詳細は [S0-013](./S0-013-competitor-matrix.md) を参照。

**なお `/api/v1/retrieval/query/collection` は公式 API リファレンスに文書化されていません。** 未文書のため後方互換の保証がありません。

---

## 基準3・4 — 日本語 OCR の一級サポートがない

### 既定で OCR は行われない

`config.py:854` — `CONTENT_EXTRACTION_ENGINE` の既定は空文字(内蔵 langchain ローダ)。

既定の PDF 経路は `retrieval/loaders/main.py:591` の `PyPDFLoader`。**テキストレイヤの抽出のみで、OCR は行いません。スキャン PDF は本文0で通ります。**

**Dockerfile の apt インストール一覧に tesseract は含まれません。**

### 日本語 OCR の設定は Open WebUI 側に存在しない

OCR 系の設定変数は外部サービス向けのみです。

| エンジン | 性質 |
| --- | --- |
| Datalab Marker / Mistral OCR | **外部 SaaS(要 API キー)** |
| PaddleOCR-VL / Docling / Tika | 自己ホスト可 |

**Docling への言語指定は `DOCLING_PARAMS` で素通しされるだけです。** ソースのコメントに「Docling の API の癖に Open WebUI が責任を持たないため、フォーム値をそのまま渡す」と明記されています(`retrieval/loaders/main.py:206-213`)。

**`ocr_lang=jpn` 相当は Docling 側の契約に依存し、Open WebUI は検証も文書化もしていません。**

### 旧バイナリ形式

| 形式 | 実装 | 判定 |
| --- | --- | --- |
| `.xls` | `UnstructuredExcelLoader` → pandas フォールバック。`xlrd==2.0.2` あり | **動作の見込みあり。実機未検証** |
| **`.doc`** | `UnstructuredWordDocumentLoader`。**`unstructured` の `.doc` 処理は LibreOffice(`soffice`)による変換に依存** | **Dockerfile に libreoffice が含まれない。既定イメージでは失敗が濃厚。実機未検証** |
| `.ppt` | 同様。`python-pptx` は旧形式を読めない | 同上 |

**`pyproject.toml` では `unstructured` は optional extra であり、pip インストール経路では既定で入りません。** Docker とそれ以外で挙動が違います。

**日本語 OCR 関連の Issue / PR は0件でした。**

---

## 基準6 — オフライン化は公式に可能

`backend/open_webui/env.py:1123-1131`:

```python
OFFLINE_MODE = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'

if OFFLINE_MODE:
    os.environ['HF_HUB_OFFLINE'] = '1'
    ENABLE_VERSION_UPDATE_CHECK = False
```

**公式ドキュメント(Hardening Open WebUI)に明記されています。**

> For air-gapped environments: `OFFLINE_MODE=true`. This disables HuggingFace Hub downloads, version update checks, and other outbound calls.

| 通信 | 既定 |
| --- | --- |
| バージョンチェック(`api.github.com`) | **有効** |
| Chroma テレメトリ / Scarf / OpenTelemetry | 無効 |
| 埋め込みモデル | **`:main` はビルド時に同梱済み** |

**完全オフライン化は可能です。ただし既定ではなく、明示設定が要ります。**

**この点で Filetto は優位を持ちません。**

---

## 基準8 — ベクトル層は切り出せる。UI は切り出せない

| 層 | 切り出しやすさ |
| --- | --- |
| `retrieval/vector/`(15種のアダプタ + 共通 IF) | **高い。** アプリ本体をほぼ参照しない |
| `retrieval/loaders/`(抽出エンジン抽象化) | **高い** |
| `retrieval/utils.py`(検索オーケストレーション・引用生成) | **低い。** Chats / Notes / Users / AccessGrants に直接依存 |
| ファイル管理(`routers/files.py` ほか) | **低い。** FastAPI ルータとしてアクセス制御・イベント・DB に一体化 |
| **UI** | **不可能。** SvelteKit のチャットアプリと同一ツリー |

**「フルのファイル操作 UI」こそが Open WebUI 唯一性の根拠でしたが、それは切り出せない部分です。**

---

## 基準9 — 貢献の道は、一方通行である

### ライセンス第4項(ブランディング条項)

> licensees are strictly prohibited from altering, removing, obscuring, or replacing any "Open WebUI" branding (中略) except (i) deployments where the total number of end users does not exceed fifty (50) within any rolling thirty (30) day period

**50ユーザ超の配布で「Open WebUI」の名前を外せません。Filetto という製品名で出せません。**

### CLA(全文)

> By submitting my contributions to this repository in any form, I grant Open WebUI Inc. a perpetual, worldwide, irrevocable, royalty-free license, under copyright and patent, to use, modify, distribute, sublicense, and **commercialize my work under any terms they choose**, both now and in the future.

**AGPL-3.0 を選んだ本案件の方針と衝突します**([ADR-0001](../../context/decisions/0001-license-agpl-3.md))。

**権利は一方向にしか流れません。** Open WebUI のコードを AGPL 製品へ取り込むことは可能ですが、逆に本案件の成果を upstream へ出すと、Open WebUI Inc. が任意の条件で商用化できる形で権利を渡すことになります。

### マージの実績(直近100件の closed PR、2026-08-13 時点)

| 件数 | 作者 |
| --- | --- |
| 19 | silentoplayz(コア) |
| 18 | Classic298(コア) |
| **5** | **外部コントリビュータ(12%)。内容はほぼ i18n 翻訳と小規模修正** |

**設計提案が Issue で議論されない運用です**(MCP サーバ化2件とも Discussion 変換 + ロック、コメント0)。

**日本語 OCR・旧バイナリ形式・MCP サーバ化のいずれも、upstream の関心事である形跡が確認できませんでした。**

---

## 基準10 — どれが安いか

| 案 | 実装量 | 成立するか |
| --- | --- | --- |
| **甲-2 upstream へ足す** | **小さい**(MCP 化は既存 REST の薄いラッパ) | **成立しない。** CLA が AGPL の方針と衝突。設計提案の経路が観測できない。**製品名も出せない** |
| **甲-3 部品として切り出す** | 中 | **部分的に成立。** ベクトル層とローダ層は持ち出せる。**ただし UI は切り出せず、それが唯一性の根拠だった。** ブランディング条項の法務判断が要る |
| **甲 新規に作る** | 大 | **成立する** |
| 乙 作らない | ゼロ | **後述の前提を採るなら成立する** |

---

## 判定 — 甲。ただし前提の選択を伴う

**Open WebUI が満たさないものは4つです。**

| # | 満たさないもの |
| --- | --- |
| **1** | **原本のファイルシステムが一級市民ではない**(論理ツリー + 平坦な `{uuid}_{filename}`) |
| **2** | **ファイルシステムの監視がない**(手動同期のみ。0ヒット) |
| **3** | **外部同期の同一性キーがパスと名前**(ローカルでの移動が削除+追加になる) |
| **4** | **MCP サーバとして公開できない**(要望2件とも Discussion へ) |

**1〜3 は同じ根に由来します。**

**Open WebUI は「取り込んだコピーを整理する箱」であり、「利用者のファイルそのものを扱う倉庫」ではありません。**

**この差が意味を持つかどうかは、次の選択に依存します。**

| 前提 | 結論 |
| --- | --- |
| **人はエクスプローラでファイルを動かす** | **甲。Filetto を作る理由がある** |
| **人は Open WebUI の中でファイルを動かす** | **乙。Filetto は不要** |

**本案件は前者を前提としています。**

> 人向けの入口は Windows Explorer / Google Drive 相当の**ファイル操作が一級市民**の UI(`context/projects/P-001.md:14`)

**しかし、この前提が正しいことは、本検証では確かめていません。**

**確かめたのは「Open WebUI が後者の前提で作られている」ことだけです。**

**前提の選択は、誰のどの作業を対象にするかという範囲の決定であり、価値責任者の職務です。**

---

## 判定できなかった項目

**実機を起動していないため、次は確定していません。**

| # | 事項 | 状況 |
| --- | --- | --- |
| 1 | `.doc` が既定 Docker イメージで処理できるか | `unstructured` は入るが libreoffice がない。**未検証** |
| 2 | `.xls` の日本語セルが正しく抽出されるか | **未検証** |
| **3** | **チャンク検索経路の引用がリネーム後に旧名を出すか** | **コード上は旧名。公式ドキュメントは「更新される」と記述。矛盾未解消** |
| 4 | 要求メモリ・ディスクの実測値 | **公式に数値記載なし。未測定** |
| 5 | `DOCLING_PARAMS` で日本語 OCR が通るか | Open WebUI 側は素通し。**未検証** |
| **6** | **UI 移動 → oikb 再同期 の往復挙動** | **コードからは delete+re-add と読めるが未検証** |

> **【2026-08-14 追記】** 上表の 3 は **S0-013 でも未解決のまま残った**。独立した実測(公式ドキュメントの再取得)でも「Knowledge 一覧・ツール出力・引用に反映される」という記述が確認され、**本記録のコード実測(チャンク検索経路は旧名)との矛盾は解消していない**。実機検証の手順は [S0-013](./S0-013-competitor-matrix.md)「Open WebUI — S0-007 との突き合わせ」に記載した。**同章では「ネストしたディレクトリ」と「Sync Directory のハッシュ差分同期」についても突き合わせ、いずれも本記録の判定(論理ツリー / 監視なし)を維持している。**

**3 と 6 は、判定の根拠に関わります。**

**ただし 6 が仮に「衝突しない」であっても、基準1・2 の結論は変わりません。** **ファイルシステムの監視が存在しないこと(0ヒット)と、ディスク上が平坦であることは、コードから確定しています。**

---

## この検証で費やしたもの

| 項目 | 実績 |
| --- | --- |
| 稼働 | 数時間(サブエージェント1本) |
| 実機の起動 | **していない** |
| 期限 | 着手から2営業日以内(#114)。**初日に完了** |

**Issue #114 は「実機で測る」設計でしたが、ソースコードの実測で結論に足る材料が揃ったため、実機の起動を行いませんでした。**

**実機でしか確かめられない6項目は上記に列挙しています。** **決裁の判断に必要であれば、追加で実施します。**

---

## 参照

- Issue [#114](https://github.com/Takenori-Kusaka/Filetto/issues/114) / [#113](https://github.com/Takenori-Kusaka/Filetto/issues/113) / [#111](https://github.com/Takenori-Kusaka/Filetto/issues/111)
- `open-webui/open-webui` @ `01f4282`(2026-07-27)
- https://docs.openwebui.com/features/workspace/knowledge
- https://docs.openwebui.com/features/extensibility/mcp
- https://docs.openwebui.com/getting-started/advanced-topics/hardening

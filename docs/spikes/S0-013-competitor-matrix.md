---
id: S0-013
stage: S0 探索(追加)
issue: "—"
status: 4グループすべて回収済み(12製品)。22製品のうち10製品分は未取得
verdict: 「22中2つのみ」は実測と一致した(Onyx / RAGFlow)。「④の空白」は狭くなったが3点が残る
date: 2026-08-14
---

# S0-013 競合製品の実測 — 決裁資料の主張を一次情報で検証し直す

## 目的

2026-08-14 の着手決裁で使った資料と、既存の調査記録([S0-002](./S0-002-alternatives.md) / [S0-007](./S0-007-value-hypothesis.md))が置いている競合に関する主張を、一次情報で検証し直します。

検証の対象は次の2点です。

| # | 検証する主張 |
| --- | --- |
| 1 | **AI 向けの入口(MCP)を公開できる製品は 22 中 2 つのみ** |
| 2 | **人向けのファイル操作 UI と、ローカル完結の RAG が重なる場所が空いている(「④の空白」)** |

---

## 調査方法

4グループを並行で走らせ、各グループが担当製品の一次情報(公式ドキュメント・リポジトリのソース・GitHub REST API・GitHub code search・LICENSE 本文・Issue / PR)を直接取得しました。

| グループ | 担当製品 | 状況 | 取得日 |
| --- | --- | --- | --- |
| 1 | AnythingLLM / Open WebUI / PrivateGPT | 回収済み | 2026-08-14 |
| 2 | LocalGPT / GPT4All / Jan | 回収済み | 2026-08-13 |
| 3 | Khoj / Onyx / Quivr | 回収済み | 2026-08-13 |
| 4 | Verba / RAGFlow / Kotaemon | 回収済み | 2026-08-14 |

**12製品を実測しました。** **元記録が挙げる22製品のうち、残る10製品分は本調査で取得していません。** **したがって本書は 22 製品の全数を置き換えるものではなく、12 製品分の差し替えです。**

**12製品いずれも実機を起動していません。** 判定はすべて文書・ソースコード・API からのものです。

グループ1は調査中に WebSearch の利用上限(200回)へ到達し、以降は GitHub API / raw ファイル / 公式ドキュメントの直接取得で裏取りしています。

---

## 12製品の全体像

| 製品 | star | MCP サーバ | フォルダ階層 | リネーム | 移動 | 既定でローカル完結 | 日本語 OCR が既定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **open-webui/open-webui** | 148,712 | **公開しない** | **あり** | **あり** | **あり** | LLM を同梱しない(キーは不要) | **OCR 自体が既定オフ** |
| **infiniflow/ragflow** | 87,989 | **公開する** | **あり** | **あり** | **記載を確認できず** | **しない**(v0.22+ で埋め込み同梱を廃止) | OCR は既定オン。**日本語は Issue #2104 / #8691** |
| **nomic-ai/gpt4all** | 77,413 | 非対応 | 製品側に無し(**OS のファイルマネージャ前提**) | 同左 | 同左 | **する** | **記載なし** |
| **Mintplex-Labs/anything-llm** | 64,699 | 公開しない | **未実装** | **未実装** | ワークスペース間のみ | 部分的(`LLM_PROVIDER` 既定が未設定) | **既定 `eng`**(`jpn` は選択可) |
| **zylon-ai/private-gpt** | 57,432 | 公開しない | 確認できず | 確認できず | 確認できず | **しない**(LLM を内蔵しない) | **既定 langs に日本語なし** |
| **janhq/jan** | 43,995 | **公開しない**(ホスト) | 確認できず | 確認できず | 確認できず | する | 記載なし |
| **QuivrHQ/quivr** | 39,397 | **非対応** | **UI が存在しない** | 同左 | 同左 | **しない**(API キー前提) | 記載なし |
| **khoj-ai/khoj** | 36,484 | 公開しない | **エンドポイントが存在しない** | 同左 | 同左 | **しない**(起動時点でモデル未設定) | **OCR 同梱。言語指定の口がコードに無い** |
| **onyx-dot-app/onyx** | 31,583 | **公開する** | **無し**(1階層) | **ファイルは不可**(プロジェクトのみ可) | プロジェクト間の付け替えのみ | **しない** | **OCR の実装自体が無い** |
| **Cinnamon/kotaemon** | 25,697 | 確認できず | 確認できず | 確認できず | 確認できず | 未確認 | 4択オプション |
| **PromtEngineer/localGPT** | 22,207 | 非対応 | 記載なし | 記載なし | 記載なし | **する** | **OCR ライブラリが依存に無し** |
| **weaviate/Verba** | 7,712 | 確認できず | 確認できず | 確認できず | 確認できず | 未確認 | 未確認 |

**集計は次のとおりです。**

| 観点 | 実測 |
| --- | --- |
| **MCP サーバとして自機能を公開する** | **2件(RAGFlow / Onyx)。** クライアントまたはホストのみ6件、非対応3件、確認できず1件(Verba、アーカイブ済み) |
| **フォルダ階層 + リネームの両方を満たす** | **2件(Open WebUI / RAGFlow)。** 移動まで満たすのは Open WebUI のみ(RAGFlow は移動の記載を確認できず) |
| **既定でローカル完結する(キー不要で即動く)** | **2件(GPT4All / LocalGPT)。ただし両者とも開発が停滞** |
| **日本語 OCR が既定で有効** | **ゼロ** |
| **`.doc` に対応** | **1件(Open WebUI。`unstructured` パッケージが必須)。** RAGFlow は拡張子を受理するが実パース品質の記載を確認できず |
| **`.xls` に対応** | **2件(Open WebUI は pandas フォールバック、PrivateGPT)。** RAGFlow は同上 |

---

## 実測結果 — 8観点

### (a) 保守状況とライセンス

| 製品 | archived | 最終 push | ライセンス |
| --- | --- | --- | --- |
| **Open WebUI** | false | 2026-08-13T22:45:02Z | **MIT ではない。** GitHub API は `license: "Other"`(NOASSERTION)。LICENSE 実測で **Open WebUI License**(BSD-3-Clause ベース + ブランディング保持条項)。例外は①直近30日ローリングでエンドユーザ50人未満 ②事前書面許諾 ③エンタープライズライセンス。**CLA 同意が要る** |
| **RAGFlow** | false | 2026-08-13 | **Apache-2.0**(LICENSE 本文を取得し、追加条項が一切ないことを確認) |
| **GPT4All** | false | **2025-05-27** | MIT、追加条項なし(LICENSE.txt 実取得。Copyright (c) 2023 Nomic, Inc.) |
| **AnythingLLM** | false | 2026-08-13T22:31:08Z | **MIT、追加条項なし** |
| **PrivateGPT** | false | 2026-08-13T16:08Z | Apache-2.0、追加条項なし |
| **Jan** | false | 2026-08-13 | **Apache-2.0 に追加条項あり。**"Attribution is requested in user-facing documentation and materials, where appropriate"。Copyright 2025 Menlo Research。**GitHub API の license は "Other"。複数の二次情報サイトが「MIT」と誤記している** |
| **Quivr** | false | **2025-07-09** | **Apache-2.0、追加条項なし**(LICENSE 実取得) |
| **Khoj** | false | 2026-08-02 | **AGPL-3.0、追加条項なし**(LICENSE 実取得。`ee/` 相当なし)。**Filetto と同じライセンス**([ADR-0001](../../context/decisions/0001-license-agpl-3.md)) |
| **Onyx** | false | 2026-08-13T22:52:08Z | **MIT Expat と `ee/` 配下の Onyx Enterprise License の混在。追加条項あり。** GitHub API は `NOASSERTION`。**`ee/` にライセンス強制の実装が存在**(`license_enforcement.py`、`backend/keys/license_public_key.pem`、`add_license_table.py`) |
| **Kotaemon** | false | 2026-07-14 | Apache-2.0(追加条項なしを確認) |
| **LocalGPT** | false | `pushed_at` 2026-07-18 | MIT、追加条項なし |
| **Verba** | **true(2026-06-08 アーカイブ)** | — | BSD-3-Clause |

**保守状況で注記すべき5件があります。**

| 製品 | 実測 |
| --- | --- |
| **Verba** | **アーカイブ済み。** README がセキュリティパッチも出ないことを明記 |
| **Quivr** | **事実上メンテナンス停止。** 最終コミット 2025-06-19、最終リリース `core-0.0.33`(2025-02-04、約18か月前)。`updated_at` は 2026-08-13 だが、これは star 等のメタデータ更新でコード変更ではない。**未対応のセキュリティ報告が open のまま**(下記) |
| **GPT4All** | **実質的な開発は 2025-02 で停止。** 最新リリース v3.10.0(2025-02-25)以降18か月リリースなし。`pushed_at` の最新コミットは CI 設定更新のみ。open issues **773件**。Issue #3605 "Is GPT4all dead?"(2025-08-05 起票)が1年以上 open |
| **LocalGPT** | **停滞。** `pushed_at` は 2026-07-18 だが、**既定ブランチ main の最新コミットは 2026-02-26。約1年で main へ3コミット。** 主要作業が `localgpt-v2` ブランチにあり未統合。open issues 24 |
| **PrivateGPT** | **star の多くは別物だった旧実装への評価。** README が "rebuilt from the ground up" と明記し、2023年の「完全オフラインで文書とチャットする PoC」から **"the open-source API layer that turns local models into production AI applications"** へ作り直されている |

**Quivr のメンテナンス停止の一次証拠**(GitHub Issues / PR API 実測):

| # | 記録 | 状況 |
| --- | --- | --- |
| 1 | **Issue #3697 "Chat IDOR - unauthenticated-of-ownership read, delete, and message injection on any chat"**(2026-07-03) | **コメント0件・open。** 本文に "reported via security advisory GHSA-w7hf-3v2c-xj58 on 2 June 2026 - no response" |
| 2 | Issue #3698 "Prompt IDOR - any authenticated user can read and overwrite any prompt"(2026-07-03) | コメント0件・open |
| 3 | PR #3696 "fix: remove unsafe allow_dangerous_deserialization in Brain.load" | **セキュリティ修正、未マージ** |
| 4 | Issue #3700 "Volunteer for maintainer review" | コメント0件・open |

**Quivr は新規採用の候補から外す状態にあります。**

**Onyx のライセンス混在は、参照時の判断を伴います。** **フォーク運用や社内配布では `ee/` を含めるか除外するかを事前に決める必要があります。**

**Khoj は本案件と同じ AGPL-3.0 です。** **参照・比較の対象として、ライセンス上の摩擦がもっとも小さい製品です。**

### (b) MCP 対応

| 製品 | サーバ | クライアント | 実測した中身 |
| --- | --- | --- | --- |
| **Onyx** | **対応** | **対応** | サーバは `backend/onyx/mcp_server/`(`api.py` / `auth.py` / `tools/search.py` / `mcp.json.template`)。README 原文「The Onyx MCP server allows LLMs to connect to your Onyx instance and access its knowledge base and search capabilities through MCP.」**Transport は HTTP POST、Port 8090、Framework は FastMCP with FastAPI wrapper、Database は None(全処理を API サーバへ委譲)。** 認証は Personal Access Token または API キーを Bearer で。**設定キー `MCP_SERVER_ENABLED=true` / `MCP_SERVER_PORT`(既定 8090)。** 起動エントリ `backend/onyx/mcp_server_main.py`、nginx テンプレートも同梱。**コードは `ee/` 配下ではないため MIT 側と判断。ただしエディション要件の明示は公式ドキュメントに無し。** クライアントは `backend/onyx/tools/tool_implementations/mcp/mcp_tool.py`、OAuth 対応、**SSRF 対策の実装あり**(`server/features/mcp/ssrf.py`) |
| **RAGFlow** | **対応** | **対応** | 公開ツールは `retrieve` / `ragflow_list_datasets` / `ragflow_list_chats`。トランスポートはレガシー SSE(`/sse`)と streamable-HTTP(`/mcp`)。self-host mode と host mode の2動作モード。起動フラグ `--enable-mcpserver` |
| **Open WebUI** | **確認できず** | **対応(Streamable HTTP のみ)** | stdio / SSE は公式プロキシ `mcpo` を挟む。**サーバ公開の記載は公式ドキュメントに確認できず。** 第三者製 `troylar/open-webui-mcp-server` は非公式(二次情報) |
| **AnythingLLM** | **確認できず** | **対応** | `anythingllm_mcp_servers.json` で外部サーバを追加。コード実測でも `server/utils/MCP/hypervisor/`、`server/endpoints/mcpServers.js`、`frontend/src/pages/Admin/Agents/MCPServers/` のみ。外部提供は REST Developer API |
| **PrivateGPT** | **確認できず** | **対応** | `private_gpt/server/mcp/mcp_service.py` ほかで `PersistentMCPClient` を実装。`mcp.types` の `Tool` / `CallToolResult` / `TextContent` / `ImageContent` / `AudioContent` を**消費側として** import |
| **Khoj** | **無し** | **対応** | `src/khoj/processor/tools/mcp.py` に `MCPClient`(stdio と sse の両対応)。DB モデル `MCPServer`、マイグレーション `0096_mcpserver.py`、導入コミット 2025-11-16 "Support using MCP tools in research mode"。**`FastMCP` / `mcp.server` のコード検索ヒット0件。`docs.khoj.dev/features/mcp` は HTTP 404** |
| **Jan** | **公開しない** | **対応(ホスト)** | 公式原文: "Jan is an MCP host that allows you to download different clients and servers and use them to accomplish a task." **方向が逆(外部ツールを呼ぶ側)** |
| **Kotaemon** | **確認できず** | **対応** | PR #813(2026-03-04 マージ)で stdio と sse に対応 |
| **LocalGPT** | **非対応** | **非対応** | GitHub code search で `mcp` の該当は package-lock.json の1件のみ |
| **GPT4All** | **非対応** | **非対応** | — |
| **Quivr** | **非対応** | **非対応** | `mcp` のコード検索ヒット **0件**(`total_count: 0`) |
| Verba | 確認できず | 確認できず | アーカイブ済み |

**12製品のうち、自機能を MCP サーバとして公開するのは RAGFlow と Onyx の2件です。**

出典: https://ragflow.io/docs/launch_mcp_server / https://ragflow.io/docs/mcp_tools

### (c) 人向けのファイル操作 UI

| 製品 | 入れ子フォルダ | リネーム | 削除 | 移動 |
| --- | --- | --- | --- | --- |
| **Open WebUI** | **対応**(Knowledge Base が「+ New Directory」でネストしたディレクトリを作る) | **対応**(ワークスペースのアイテムメニューからその場で。**公式ドキュメントは Knowledge 一覧・ツール出力・引用にも反映されると記述**) | **対応**(Settings > Data Controls > Manage Files。削除時は関連 Knowledge Base とベクタ埋め込みまでディープクリーンアップ) | **対応**(ディレクトリのリネームと別の親への移動が、中の files に影響を与えずに可能) |
| **RAGFlow** | **構築できる** | **ファイル / フォルダとも可能** | **個別および一括で可能**(root と `.knowledgebase` は削除不可) | **明示的な記載を確認できず** |
| **Onyx** | **無し(1階層のフラットな束ね)** | **プロジェクトのリネームは可能(`PATCH /{project_id}`)。ファイルのリネームは該当エンドポイントが存在しない** | 対応 | **プロジェクト間の付け替えのみ**(`backend/onyx/server/features/projects/api.py` 実測) |
| **AnythingLLM** | **未実装** | **未実装** | 記載を確認できず | **ワークスペースへの移動のみ。フォルダ間移動は未実装** |
| **Khoj** | **該当エンドポイントが存在しない** | 同左 | **対応**(`src/khoj/routers/api_content.py` はアップロードと削除のみ) | 同左。**Web UI のコンポーネント一覧にファイル管理用コンポーネントが無い** |
| **GPT4All** | **製品側に無い**(既存のローカルフォルダにリンクする方式。**階層操作は OS のファイルマネージャで行う前提**) | 同左 | 同左 | 同左 |
| **Jan** | 記載を確認できず | 記載を確認できず | 記載を確認できず | 記載を確認できず(アップロード口 + プロジェクト単位のグルーピングまで) |
| **LocalGPT** | 記載なし | 記載なし | 記載なし | 記載なし(アップロード口のみ) |
| **PrivateGPT** | 記載を確認できず | 記載を確認できず | 記載を確認できず | 記載を確認できず。**公式が `/ui` を "for testing purposes" / "a demonstrator, not the core product" と明言** |
| **Quivr** | **UI が存在しない** | 同左 | 同左 | 同左。**ルートツリー実測でフロントエンド・バックエンドのアプリケーションディレクトリが削除済み**(ツリー要素数285のみ)。README 原文 "This is the core of Quivr, the brain of Quivr.com." **現在は Python の RAG ライブラリ(`quivr-core`)であり、アプリケーションではない** |
| Kotaemon / Verba | 確認できず | 確認できず | 確認できず | 確認できず |

**AnythingLLM の Issue #3888(2025-05-27 起票、Open)** は、現状を "a folder to group files as they are scraped" と述べ、フォルダ階層の本格運用・フォルダ間移動・リネーム・タグ付けを要望として挙げています。

**GPT4All の方式だけが「人は OS のファイルマネージャでファイルを動かす」を前提としています。** **ただし対応拡張子が4種で、開発は 2025-02 で停止しています。**

出典: https://ragflow.io/docs/manage_files

### (d) 既定でローカル完結するか

| 製品 | 判定 | 根拠 |
| --- | --- | --- |
| **LocalGPT** | **完結する** | README: "fully private, on-premise Document Intelligence platform" / "no data ever leaves your machine"。Ollama が既定(`ollama pull qwen3:0.6b` / `qwen3:8b`)。IBM watsonx はオプション |
| **GPT4All** | **完結する** | "No API calls or GPUs required"。Nomic API はオプトイン(既定で無効) |
| **Jan** | **完結する** | "runs 100% offline"。**ただし README の表現は "Everything runs locally when you want it to" であり、UI 上にクラウドモデルの導線が並置される** |
| **Open WebUI** | **API キーは既定で不要。ただし LLM を同梱しない** | `config.py` 実測で `ENABLE_OLLAMA_API` 既定 True、`ENABLE_OPENAI_API` 既定 True、**`OPENAI_API_KEYS` 既定は空文字**。埋め込みも既定ローカル(`RAG_EMBEDDING_ENGINE` 既定 `''`、`sentence-transformers/all-MiniLM-L6-v2`)。**`OLLAMA_BASE_URL` 既定は空で、Ollama 相当が別プロセスで要る** |
| **AnythingLLM** | **部分的** | README「runs locally by default with zero setup friction」。**しかし `docker/.env.example` 実測で `LLM_PROVIDER` の行はすべてコメントアウト。既定の LLM プロバイダは未設定で、初回オンボーディング UI で利用者が選ぶ。「ローカル LLM が既定」ではなく選択肢の一つ。** 埋め込みは既定ローカル(`EMBEDDING_ENGINE='native'` / `Xenova/all-MiniLM-L6-v2`、187〜188行)、ベクタ DB も既定ローカル(LanceDB) |
| **Khoj** | **完結しない** | **起動時点でチャットモデルが未設定で、`http://localhost:42110/server/admin` で利用者が設定する。** ローカル LLM は「別途の設定手順」として提示。**「キー不要で即動く既定構成」が存在しない** |
| **Onyx** | **完結しない** | README は自己ホスト LLM を「サポートされる選択肢」として列挙。Admin Panel → Language Models で選ぶ。**既定プロバイダの有無は公式ドキュメント上「確認できず」。エアギャップ対応の主張は onyx.app のマーケティング記事(二次情報)のみで、`docs.onyx.app` に該当記述なし** |
| **PrivateGPT** | **完結しない** | **LLM を内蔵しない。**"PrivateGPT does not run models itself. It connects to any OpenAI-compatible inference server."。`OPENAI_API_BASE` で外部の OpenAI 互換サーバを指す(API キー自体は既定で不要)。**文書解析も既定で別サーバ依存**: `settings.yaml` 実測で `docling.mode` 既定 `api`(`${PGPT_DOCLING_MODE:api}`)、`api_base` 既定 `http://localhost:5001` |
| **Quivr** | **完結しない** | README が **"Add your API Keys to your environment variables"** と明記。Ollama は「も対応している」位置づけ |
| **RAGFlow** | **完結しない** | v0.22.0 以降、埋め込みモデル同梱版(full イメージ)を廃止。`docker/.env` に "v0.22+ doesn't include embedding models." と明記。ログイン後に Model providers で API キーを設定し、System Model Settings で既定モデルを指定する手順が要る |
| Kotaemon / Verba | 未確認 | 本調査では測っていない |

### (e) 日本語 OCR とスキャン PDF

| 製品 | 実測 |
| --- | --- |
| **Khoj** | **OCR は既定で有効(同梱)。** `pyproject.toml` の**主依存**に `rapidocr-onnxruntime == 1.4.4`(オプション extras ではない)。Dockerfile に "Required by RapidOCR" のコメント付き apt 依存。**ただし実装は `loader = RapidOCR()` と引数なしで既定モデルを生成し、言語指定のパラメータも設定キーもコード上に存在しない。日本語モデルへの切替経路が無い。** OCR 対象拡張子は `.png` / `.jpg` / `.jpeg` / `.webp` のみ |
| **RAGFlow** | **DeepDoc が既定の PDF パーサ**で、OCR + 表構造認識 + レイアウト認識を行う。**スキャン PDF は既定で処理対象**。**ただし日本語は弱点の可能性が高い**: deepdoc/README に対応言語の記載がなく、Issue #2104 に「English と Chinese では良好だが他言語では優れない」旨の記述。多言語 OCR の Issue #8691 は 2026-07-27 時点で **open** |
| **AnythingLLM** | **OCR は既定で内蔵**(`collector/package.json` に `tesseract.js: ^6.0.0`)。**`OCRLoader/validLangs.js` に `jpn: "Japanese"` を含む(`jpn_vert` 縦書きは無し)。ただし `OCRLoader/index.js` のコンストラクタ既定は `{ targetLanguages = "eng" }`。日本語は `options?.ocr?.langList` 経由で追加が要る** |
| **PrivateGPT** | **OCR は既定で有効**(`use_ocr: true` / `ocr_model: easyocr`)。**ただし `langs` 既定が `["en-US", "fr-FR", "de-DE", "es-ES"]` で日本語を含まない。** EasyOCR 自体は日本語に対応するが `PGPT_DOCLING_LANGS` の明示設定が要る |
| **Open WebUI** | **OCR は既定で無効**(`CONTENT_EXTRACTION_ENGINE` 既定 `''`)。選択式の外部エンジンは Tika / Docling / Datalab Marker / **Mistral OCR(外部 API・キー必要)** / PaddleOCR-VL。**日本語 OCR の既定値の明記は確認できず** |
| **Onyx** | **OCR の実装が存在しない。** `extract_file_text.py` の `pdf_to_text` / `read_pdf_file` は**テキストレイヤ抽出のみ**で、tesseract 相当への依存が無い。**テキストレイヤの無い PDF は空文字が返る。** 代替は2つで、いずれも既定オフ: ①**Unstructured API(外部 SaaS へファイルを送信。`KV_UNSTRUCTURED_API_KEY`)** ②ビジョン LLM 解析。**日本語に関する記載はコード・ドキュメントとも無し** |
| **Kotaemon** | OCR は Azure DI / Adobe / Docling / PaddleOCR の4択オプション。日本語 UI ロケールの PR #812 は未マージ |
| **LocalGPT** | **OCR ライブラリが依存に1つも存在しない**(pytesseract / paddleocr / easyocr / rapidocr / surya いずれも不在)。`docling` は入るが README は「現状 PDF のみ対応」と明記。日本語の記載なし |
| **GPT4All** | OCR の記載なし。日本語の記載なし |
| **Jan** | OCR の記載なし。日本語の記載なし |
| **Quivr** | OCR・日本語ともに記載なし |
| Verba | 未確認 |

**日本語 OCR が既定で有効な製品は、12製品中ゼロです。**

**OCR を既定で通す製品は3件(Khoj / RAGFlow / PrivateGPT)ありますが、いずれも日本語へ向いていません。** **Khoj は言語指定の口がコードに存在せず、PrivateGPT は既定 langs に日本語を含まず、RAGFlow は日本語の精度を測った一次情報が確認できません。**

### (f) 旧バイナリ形式と受理拡張子

| 製品 | 実測 |
| --- | --- |
| **Open WebUI** | `backend/open_webui/retrieval/loaders/main.py` 実測。**`.doc` → `UnstructuredWordDocumentLoader`(`unstructured` パッケージ必須。未導入時はエラー "Processing .doc files requires the 'unstructured' package.")。`.xls` → `UnstructuredExcelLoader`、未導入時は pandas へフォールバック**(内蔵 `ExcelLoader`) |
| **PrivateGPT** | 受理拡張子(`private_gpt/components/readers/registry.py` 実測): `.csv .docx .eml .htm .html .md .pdf .pptx .psv .shtm .shtml .stm .tsv .txt .xht .xhtml .xls .xlsx`。**`.xls` は対応、`.doc` は非対応** |
| **RAGFlow** | `api/utils/file_utils.py` の `filename_type()` が doc / xls / ppt / wps / rtf を受理する。**ただし実パース品質の明記は確認できず** |
| **Onyx** | 受理拡張子(`file_types.py` 実測): `.xlsx .xlsm .csv .tsv .txt .md .mdx .conf .log .json .xml .yml .yaml .sql .pdf .docx .pptx .eml .epub .html .png .jpg .jpeg .webp`。**`.doc` / `.xls` / `.ppt` は許可リストに存在せず非対応。** オフィス文書は `markitdown` と `openpyxl` を使用 |
| **AnythingLLM** | 受理拡張子(`collector/utils/constants.js` 実測): `.txt .md .org .adoc .rst .html .csv .json .docx .odt .pdf .epub .pptx .odp .xlsx .mbox` + 音声・動画・画像。**`.doc` / `.xls` は受理リストに存在しない(非対応と実測で断定できる)** |
| **Khoj** | パーサは `docx` / `markdown` / `notion` / `org_mode` / `pdf` / `plaintext`(`pymupdf 1.24.11`、`docx2txt 0.8`)。**`.doc` / `.xls` は非対応。`.xlsx` / `.pptx` も非対応**(パーサディレクトリ自体が存在しない) |
| **Jan** | PDF / Markdown / DOCX / XLSX / PPTX / コード。**`.xls` / `.doc` の記載なし** |
| **GPT4All** | **`.txt` `.pdf` `.md` `.rst` の4種のみ。`.docx` / `.xlsx` / `.pptx` すら対象外** |
| **LocalGPT** | `.xls` / `.doc` の記載なし |
| **Kotaemon** | `.doc` / `.docx` は Unstructured の追加インストールが要る |
| **Quivr** | 既定パーサの網羅範囲を確認できず |
| Verba | 未確認 |

### (g) 導入の手数と要求リソース

| 製品 | 実測 |
| --- | --- |
| **Open WebUI** | **12製品中もっとも容易。`docker run` 一行。** `pip install open-webui` → `open-webui serve` も可 |
| **Onyx** | **実質1コマンド。** `uv tool install onyx-cli && onyx-cli deploy install`、または `curl -fsSL https://onyx.app/install_onyx.sh` をシェルへパイプする手順。**Windows PowerShell の公式手順あり**(`irm https://onyx.app/install_onyx.ps1` を `iex` へパイプ)。資源要件(公式): **Lite 最小 2 vCPU / 2GB RAM / 10GB Disk、Standard 最小 4 vCPU / 10GB RAM / 32GB + インデックス対象データの約2.5倍**。K8s / Helm、Terraform provider も提供 |
| **GPT4All** | **docker 不要。GUI インストーラのみ。** `pip install gpt4all` も可 |
| **Jan** | デスクトップアプリのインストーラ配布で容易。**ソースビルドは Node.js ≥20 / Yarn ≥4.5.3 / Make ≥3.81 / Rust。docker compose の記載なし** |
| **AnythingLLM** | `docker/` に compose と `.env.example`。ワンクリックデプロイのボタン(Docker / AWS / GCP / DigitalOcean)。ソース起動は `yarn setup` → 3プロセス |
| **Khoj** | docker compose は**3ステップ**(yml をダウンロード → **環境変数の編集が必須** → up)。pip 版は2ステップ。**メモリ要件の記載なし。** 既定ポート 42110 |
| **LocalGPT** | **docker compose 一発ではない。5ステップ。Ollama をホスト側へ別途インストールする必要があり、コンテナ内で完結しない。** RAM 8GB以上(16GB推奨) |
| **RAGFlow** | CPU 4コア以上 / RAM 16GB以上 / Disk 50GB以上。**`vm.max_map_count` ≥ 262144 のカーネルパラメータ変更が要る**(Elasticsearch 用)。`MEM_LIMIT` の既定は約8GB。**「docker compose 一発」ではない** |
| **Quivr** | `pip install quivr-core` + Python 5行程度。**利用者側で UI・永続化・認証・ファイル管理をすべて自作する必要がある** |
| **PrivateGPT** | **12製品中もっとも重い。docker compose ではない。** Python **3.11 固定**(3.10 と 3.12 以降は非対応と docs 明記)、`uv` または Homebrew、別途 OpenAI 互換 LLM サーバ、さらに Docling API サーバ。モデル pull 約24GB の例。データ格納は `~/.local/share/private-gpt/` / `%LOCALAPPDATA%\private-gpt\`、`PGPT_HOME` で上書き可。**公式クイックスタートに Docker の記載は確認できず** |
| **Kotaemon** | **RAM 要件は未確認** |
| Verba | 未確認 |

**Windows 向けの公式手順を持つのは Onyx(PowerShell)と PrivateGPT(データ格納先の記載)の2件です。**

### (h) 提供形態

| 製品 | 実測 |
| --- | --- |
| **Open WebUI** | エンタープライズプランあり(custom theming and branding / SLA / LTS)。**ブランディング変更権がエンタープライズ側にある** |
| **Onyx** | **CE(MIT)/ Cloud(SOC2 Type II・GDPR)/ Self-Host Enterprise Edition の3形態** |
| **AnythingLLM** | Hosted Instance(my.mintplexlabs.com)+ デスクトップアプリ |
| **PrivateGPT** | Zylon が商用側。推論サーバ・並列処理 / ロードバランシング・Kubernetes・ガバナンス・**LDAP / Active Directory**・監査ログ・ワークフロー自動化 |
| **RAGFlow** | クラウド版 https://cloud.ragflow.io が存在する(**価格は二次情報のため本書では扱わない**) |
| **Khoj** | **Khoj Cloud は 2026-04-15 に廃止済み。** `deprecationBanner.tsx` に "Khoj Cloud is being deprecated on April 15, 2026." を実装(追加コミット 2026-03-25)。**README はこれに追随しておらず "available as a cloud service" のまま。記述が古い** |
| **LocalGPT** | SaaS なし。問い合わせフォーム経由の受託導入のみ |
| **GPT4All** | 本体は無償 OSS。**旧 enterprise ページは接続拒否(ECONNREFUSED)で現存を確認できず。** Nomic Atlas は別製品 |
| **Jan** | **商用版・クラウド版は一次情報で確認できず** |
| **Quivr** | 商用条件の具体的記載を README 内に確認できず |
| Kotaemon / Verba | 未確認 |

---

## Open WebUI — S0-007 との突き合わせ

**グループ1の報告(公式ドキュメント由来)と、[S0-007](./S0-007-value-hypothesis.md) のソースコード実測を突き合わせます。**

### 1. 「ネストしたディレクトリ」は論理ツリーか、ディスク上の実体か

| 出所 | 記述 |
| --- | --- |
| グループ1(公式ドキュメント) | Knowledge Base が**ネストしたディレクトリ**に対応。「+ New Directory」で作成。**ディレクトリのリネームと別の親への移動が、中の files に影響を与えずに可能** |
| S0-007(ソース実測) | `models/knowledge.py:63-79` の `KnowledgeDirectory`(`parent_id` を持つ **DB ツリー**)。ファイル実体は `storage/provider.py` が **`{uuid}_{filename}` の平坦な名前**で `data/uploads/` に置く。**公式ドキュメント自身が "internal container model, not a real filesystem" と記述** |

**両者は矛盾しません。** **グループ1が観測したのは UI 上の振る舞いであり、S0-007 が実測したのはその実装が DB 上の論理ツリーであることです。** **「中の files に影響を与えずに移動できる」という性質そのものが、ディレクトリがファイル実体の置き場ではないことの帰結です。**

**判定は S0-007 のまま維持します。ディスク上は平坦です。**

### 2. 「リネームが引用にも反映される」— 矛盾は未解消のまま

| 出所 | 記述 |
| --- | --- |
| グループ1(公式ドキュメント) | 名称は **Knowledge 一覧・ツール出力・引用にも反映される** |
| S0-007(ソース実測) | 経路で分かれる。**フルコンテキスト経路**は `retrieval/utils.py:1477, 1554` で **DB から引き直す(新しい名前)**。**チャンク検索経路**は**ベクタ DB のメタデータをそのまま使う**。索引時に `{'name': file.filename}` を焼き付け(`routers/retrieval.py:1880` ほか)、リネームしても更新されない(**旧い名前**) |

**この矛盾は未解消です。** **公式ドキュメントの記述と、コード実測から読める挙動が一致しません。**

**確定させるには実機検証が要ります。** 手順は「ファイルを索引 → リネーム → チャンク検索がヒットする質問を投げ、引用に出る名前を見る」です。**本書ではこれを未確認事項として残します。**

### 3. 「Sync Directory のハッシュ差分同期」と「ファイル監視0ヒット」

| 出所 | 記述 |
| --- | --- |
| グループ1(公式ドキュメント) | ローカルフォルダを**ハッシュ比較で差分同期**(新規・変更・削除のみ処理) |
| S0-007(ソース実測) | **`watchdog` / `inotify` / `watchfiles` / `Observer` が backend 全体で0ヒット。** UI の Sync Directory は**ブラウザ側の File System Access API で、毎回利用者がフォルダを選び直す手動操作**(`KnowledgeBase.svelte:493-522`)。同期の同一性キーは `indexed_files[(file_path, file_model.filename)]`(`routers/knowledge.py:1822-1912`)で、**ハッシュは checksum として持つが、キーではない** |

**両者は矛盾しません。** **「ハッシュ比較で差分を出す」ことと「同一性キーが(パス, ファイル名)である」ことは両立します。** **キーがパスと名前である以上、ローカル側でのリネーム・移動は「削除 + 新規追加」になります。**

**そして「差分同期がある」ことは「監視がある」ことを意味しません。同期は手動起動です。**

**判定は S0-007 のまま維持します。**

### 4. ライセンスの一致

**グループ1の実測(Open WebUI License / BSD-3-Clause ベース + ブランディング保持条項 / 例外は直近30日ローリングでエンドユーザ50人未満・事前書面許諾・エンタープライズライセンス / CLA 同意)は、S0-007 の基準9 の記録と一致します。**

---

## 既存の主張との突き合わせ

### 主張1「MCP を公開できる製品は 22 中 2 つのみ」— 実測と一致した

**元記録が挙げていた2製品と、実測で該当した2製品は一致します。取り違えはありません。**

| | 製品 |
| --- | --- |
| **元記録が挙げていた2件** | **Onyx / RAGFlow** |
| **12製品の実測で該当した2件** | **Onyx / RAGFlow** |

出所を追跡した結果は次のとおりです。

| # | 記録 | 記述 |
| --- | --- | --- |
| 1 | `tmp/process-compass-feedback-draft.md:278` | 「自機能を MCP サーバとして公開するローカル製品は 22製品中2つ(**Onyx / RAGFlow**)のみ」。**製品名を挙げている唯一の記録** |
| 2 | `tmp/feedback-03-what-we-should-have-built.md:160` | 同主張(**製品名の記載なし**) |
| 3 | `tmp/feedback-00-index.md:125` | 「競合マップ(22製品)」を「『空白がある』の根拠」と位置づける |

**[S0-002](./S0-002-alternatives.md) にはこの主張が存在しません。** **同記録を全文確認しましたが、MCP・Onyx・RAGFlow・22製品のいずれの語も含まれていませんでした。** **S0-002 は層A(パース)と層B(検索)の候補比較であり、競合製品の一覧ではありません。**

**本調査が追加したのは次の3点です。**

| # | 追加した裏付け |
| --- | --- |
| 1 | **RAGFlow のサーバ公開の実装詳細**(公開ツール3種、SSE と streamable-HTTP、self-host / host の2モード、`--enable-mcpserver`) |
| 2 | **Onyx のサーバ公開の実装詳細**(`backend/onyx/mcp_server/`、HTTP POST、Port 8090、FastMCP with FastAPI wrapper、`MCP_SERVER_ENABLED` / `MCP_SERVER_PORT`、`backend/onyx/mcp_server_main.py`) |
| 3 | **他10製品がサーバ側を持たないことの実測**(Khoj は `FastMCP` / `mcp.server` のコード検索0ヒット、Quivr は `mcp` 自体が0ヒット、Jan は公式が「ホスト」と明言) |

**MCP クライアント側は広く実装されています。** Open WebUI / AnythingLLM / PrivateGPT / Jan / Kotaemon / Khoj の6製品がクライアントまたはホストとして対応し、**方向は「外部ツールを呼ぶ側」です。**

**ただし、次の2点が確認できません。**

| # | 確認できなかったこと |
| --- | --- |
| 1 | **22製品の一覧そのものが、リポジトリのどこにも記録されていません。** `docs/` 配下に競合一覧の記録は存在せず、集計結果の要約が `tmp/` 配下の3ファイル(いずれも未コミットのフィードバック草稿)に書かれているだけです |
| 2 | **残る10製品を本調査は取得していません。** そこにサーバ公開の製品が含まれる可能性を否定できません |

**「22 中 2 つ」は、12製品の範囲では正確でした。分母(22製品の一覧)には検証できる記録がありません。**

### 主張2「④の空白」

**リポジトリ内に「④の空白」という語での定義は存在しません。** 該当しうる記述は2か所あり、**両者で ④ の指す対象が異なります。**

| 記録 | 記述 | ④ が指すもの |
| --- | --- | --- |
| `docs/decisions/P-001-kickoff-decision.md`「6本の調査の結論」の S0-007 節 | 「満たさないものが4つあります。①原本のファイルシステムが一級市民ではない、②ファイルシステムの監視がない(0ヒット)、③外部同期の同一性キーがパスと名前、**④MCP サーバとして公開できない**」 | **Open WebUI の4番目の不足項目** |
| `docs/spikes/S0-007-value-hypothesis.md:22` | 「**Open WebUI は、22製品中で唯一「フルのファイル操作 UI × ローカル RAG」を両立しています**」 | 重なりの記述。**ただし ④ という番号は振られていない** |

**「人向けファイル操作 UI × ローカル完結 RAG の重なりが空いている」という象限としての定義は、記録に無しです。**

**そのうえで、S0-007 の「唯一」は、本調査の実測と食い違います。**

| 観点 | S0-007 の記述 | S0-013 の実測 |
| --- | --- | --- |
| ファイル操作 UI を持つローカル RAG | **Open WebUI のみ** | **RAGFlow も入れ子フォルダ・リネーム・個別/一括削除を持つ** |
| MCP サーバの公開 | Open WebUI は**できない**(要望2件とも Discussion へ変換・ロック) | **RAGFlow と Onyx はできる** |

**S0-007 は Open WebUI 1製品のソース実測であり、他の21製品の再確認を行っていません。** **「唯一」という限定は、その21製品側の判定に依存します。RAGFlow については、その判定が実測と合いません。**

**ただし「ファイル操作 UI の強さと RAG 能力が反比例する」という既存の観測は、12製品の実測でも保たれています。** **フォルダ階層とリネームの両方を持つのは Open WebUI と RAGFlow の2件のみで、残る10製品はアップロード口までです。**

---

## 「④の空白」の再定義 — 12製品を通した結果

**要件ごとに、満たす製品を並べます。**

| 要件 | 満たす製品 | 件数 |
| --- | --- | --- |
| MCP サーバ公開 | **RAGFlow / Onyx** | 2 |
| フォルダ階層 + リネーム | **Open WebUI / RAGFlow** | 2 |
| 既定でローカル完結(キー不要で即動く) | **GPT4All / LocalGPT。ただし両者とも開発が停滞**(GPT4All は 2025-02 で実質停止・open issues 773件、LocalGPT は main へ約1年で3コミット) | 2 |
| **日本語 OCR が既定で有効** | **無し** | **0** |
| **人がエクスプローラで動かしたファイルへの追従(ファイル監視)** | **無し**(Open WebUI について `watchdog` / `inotify` / `watchfiles` / `Observer` が backend 全体で0ヒットであることを [S0-007](./S0-007-value-hypothesis.md) が実測。**他11製品はファイル監視の記載を確認できず**) | **0** |
| **確かめる箇所へ1クリックで到達させる導線** | **無し**(12製品のいずれにも該当する記載を確認できず) | **0** |

**下3行が、12製品を通して埋まっていない場所です。**

**上3行は埋まっています。しかも重なりません。** **MCP サーバを公開する2製品(RAGFlow / Onyx)は、いずれも既定でローカル完結しません。既定でローカル完結する2製品(GPT4All / LocalGPT)は、いずれも MCP サーバもファイル操作 UI も持ちません。**

**「MCP サーバ公開」「フォルダ階層 + リネーム」「既定でローカル完結」の3つを同時に満たす製品は、12製品中ゼロです。**

### 残る差分を RAGFlow の実測値と並べる

**RAGFlow は本案件の主張ともっとも近い位置にあります。差分を実測値と並べます。**

| # | 残る差分 | RAGFlow の実測値 | 差分が残ると言える理由 |
| --- | --- | --- | --- |
| **1** | **日本語 OCR** | DeepDoc が既定で OCR + 表構造認識 + レイアウト認識。**deepdoc/README に対応言語の記載なし。Issue #2104 に「English と Chinese では良好だが他言語では優れない」旨。多言語 OCR の Issue #8691 は 2026-07-27 時点で open** | **日本語の精度を測った一次情報が存在しない。** **12製品を通して、日本語 OCR が既定で有効なものはゼロ。** 本案件は日本語スキャン PDF と中国語字形の混入を [S0-006](./S0-006-ocr-glyph.md) で実測している |
| **2** | **既定でローカル完結するか** | **完結しない。** v0.22.0 以降、埋め込みモデル同梱版を廃止(`docker/.env` に "v0.22+ doesn't include embedding models.")。Model providers での API キー設定と System Model Settings での既定モデル指定が要る | 既定でローカル完結する2製品(GPT4All / LocalGPT)は、**いずれもファイル操作 UI と MCP サーバの両方を持たず、開発も停滞している。** 本案件は外部 API なしで検索と RAG が成立することを [S0-003](./S0-003-parser-and-hybrid.md) / [S0-004](./S0-004-rag-fitness.md) で実測している |
| **3** | **Windows での導入容易性** | CPU 4コア以上 / RAM 16GB以上 / Disk 50GB以上。**`vm.max_map_count` ≥ 262144 のカーネルパラメータ変更が要る**。`MEM_LIMIT` 既定 約8GB。**「docker compose 一発」ではない** | カーネルパラメータの変更は、Windows では WSL2 側の設定を伴う。**Windows 向けの公式手順(PowerShell)を持つのは Onyx。その Onyx は既定でローカル完結せず、OCR の実装を持たない。** **本調査は Windows での実機検証を行っていない** |
| **4** | **エクスプローラでの移動への追従** | **「移動(move)」の明示的記載を確認できず。** フォルダ構築・リネーム・削除は文書化されている | **RAGFlow のフォルダが原本のディレクトリか論理ツリーかを確認していない。** Open WebUI については論理ツリーであることがソース実測で確定している。**12製品中、OS のファイルマネージャでの操作を前提に置くのは GPT4All のフォルダ紐付け方式だけで、その GPT4All は対応拡張子4種・開発停止(2025-02)である** |

**4 は本案件の中核と直結します。** **決裁は「人はエクスプローラでファイルを動かす」という前提を採る決定を下しています**(`docs/decisions/P-001-kickoff-decision.md`)。**RAGFlow がその前提を満たすかどうかは、本調査では確定していません。** **確定していないのは「満たさない」ではなく「測っていない」です。**

---

## 未確認事項

| # | 事項 | 状況 |
| --- | --- | --- |
| **1** | **22製品のうち残る10製品** | **本調査で取得していない。サーバ公開の製品が含まれる可能性を否定できない** |
| **2** | **22製品の一覧そのもの** | **リポジトリに記録が無い。`tmp/` の集計要約3件のみ** |
| **3** | **Open WebUI のチャンク検索経路の引用が、リネーム後に旧名を出すか** | **未解決。公式ドキュメントは「反映される」、S0-007 のコード実測は「旧名」。実機検証が要る**(手順は本書「Open WebUI — S0-007 との突き合わせ」2 に記載) |
| **4** | **Onyx のエアギャップ運用可否** | **一次裏付けなし。マーケティング記事(二次情報)のみで、`docs.onyx.app` に該当記述なし** |
| 5 | Onyx で LLM 設定が初期セットアップの必須工程か、既定プロバイダが存在するか | 公式ドキュメント上「確認できず」 |
| **6** | **Onyx の MCP サーバが OSS(CE)版で使えるかのドキュメント上の明示** | **コード配置(`ee/` 配下ではない)から MIT と判断。明示は無し** |
| 7 | Khoj の RapidOCR 既定モデルが日本語を含むか | 未確認 |
| 8 | Khoj Cloud 廃止後の app.khoj.dev の実稼働状況 | 未確認 |
| 9 | Khoj のメモリ要件 | 記載なし |
| 10 | Quivr の既定パーサの網羅範囲 / 過去のライセンス変遷 | 未確認 |
| **11** | **RAGFlow の日本語 OCR 精度の一次情報** | **存在を確認できず。Issue の記述による推定に留まる** |
| **12** | **RAGFlow の `.xls` 実パース可否** | **`filename_type()` が受理することのみ確認。パース品質の記載を確認できず** |
| 13 | RAGFlow の「移動(move)」操作の有無 | 公式文書に明示的記載を確認できず |
| 14 | RAGFlow のフォルダが原本のディレクトリか論理ツリーか | 未確認 |
| 15 | Kotaemon の RAM 要件 / ローカル完結の可否 | 未確認 |
| 16 | RAGFlow クラウド版の価格 | 二次情報のみ |
| 17 | GPT4All の enterprise ページの現存 | **接続拒否(ECONNREFUSED)。確認できず** |
| 18 | Jan の商用版・クラウド版の有無 | **一次情報で確認できず** |
| 19 | LocalGPT / GPT4All / Jan の日本語 OCR と旧バイナリ形式 | **3件とも一次情報が存在しない** |
| 20 | Verba の (b)〜(h) | アーカイブ済みのため未取得 |
| **21** | **12製品いずれも実機を起動していない** | **本書はすべて文書・ソース・API からの判定** |

---

## 参照

- RAGFlow MCP: https://ragflow.io/docs/launch_mcp_server / https://ragflow.io/docs/mcp_tools
- RAGFlow ファイル管理: https://ragflow.io/docs/manage_files
- `onyx-dot-app/onyx`(旧 Danswer)
- `janhq/jan`(`menloresearch/jan` は同リポジトリへのリダイレクト)
- [S0-002](./S0-002-alternatives.md) — 対案の比較と実測
- [S0-007](./S0-007-value-hypothesis.md) — Open WebUI の実測
- [S0-006](./S0-006-ocr-glyph.md) — 日本語 OCR の字形混入
- `docs/decisions/P-001-kickoff-decision.md` — 着手決裁

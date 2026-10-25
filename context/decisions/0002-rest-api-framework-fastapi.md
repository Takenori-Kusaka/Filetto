# ADR-0002: REST API の Web フレームワークを FastAPI(版固定)とする

## ステータス

採用(2026-10-25)。起案は AI の担い手(Claude)。採否は技術判断者 Takenori Kusaka(プロジェクトのスレッドの判断カードで「FastAPI(版固定)」を選択)。

## コンテキスト

F-001 Task-2(WebUI の削除をゴミ箱への移動にする)で、REST API の入口が初めて要る。旧 ADR-0006(2026-08-12、現在は廃止したディレクトリにあった)はバックエンドを Python 3.12 と決めたが、Web フレームワークは決めていなかった。

制約:

- 公式 MCP Python SDK(`mcp` 2.3.0)のサーバを同じプロセスに同居させる(F-001 Task-3 以降)。SDK は Starlette・uvicorn・Pydantic v2 を必須依存に持つ
- Docling などの文書処理と同じプロセスで動く。メタデータは stdlib の SQLite(ADR-0010 の決定。現在は `specs/F-002/spec.md`)
- 外部との契約(F-003)を型で守りたい。保守は1人

比較の材料: `/mnt/project-files/research/reports/Python Web フレームワーク比較 2026.md`(2026-10-25 時点の調査。プロジェクトの共有フォルダ)

## 決定

- REST API は **FastAPI** で書く
- 0.x で互換性を壊す変更が多いため、`fastapi` と `starlette` を**マイナー版まで固定**する(`pyproject.toml`: `fastapi>=0.162,<0.163`、`starlette>=1.10,<1.11`)。版を上げるときは独立した変更にする
- `fastapi[standard]` は使わない(FastAPI Cloud の CLI などを持ち込まないため)。要る依存は個別に足す
- テストクライアントの依存は `httpx2`(Starlette 1.10 で `httpx` は非推奨)

## 検討した選択肢

各案の性質は調査報告書のとおり。採らなかった理由の欄は、判定者 Takenori Kusaka の指示により AI の担い手が代理記入した(2026-10-25。判定者が PR の承認時に査読する)。

| 案 | 性質(調査の要約) | 採らなかった理由 |
| --- | --- | --- |
| Starlette + Pydantic を直接使う | 依存が最小で MCP SDK と同じ土台。入力検査と OpenAPI の生成は自前 | 入力検査と OpenAPI の生成を自前で書き続ける負担が、FastAPI を足して増える依存(MCP SDK と共有しない小さな2パッケージ)より重い。FastAPI の版の揺れが負担になったときの退避先として残す |
| Litestar 2.x | 組織運営で保守者が複数。公式 MCP SDK は `@asgi` でのマウント(文書にない方法)。3.x への移行が控える | 公式 MCP SDK との同居が文書にない方法になり、Starlette も別に入って土台が二重になる。3.x の正式版が出ておらず、採用直後に移行作業が控える。保守体制の良さはこれらを上回らない。3.x の正式版が出た時点で見直す |
| BlackSheep / Falcon / Quart / Flask / Sanic / Robyn / Emmett / Django + Ninja | 報告書の比較で、上の3案を上回る点が見つからなかった | Flask は WSGI で ASGI の MCP SDK と同居しにくい。Quart は Python 3.13 以上が必須。Django + Ninja は ORM と移行の仕組みが stdlib の SQLite の方針と重なる。Falcon は検査と OpenAPI が自前。BlackSheep・Robyn・Emmett・Sanic は保守者が少ないか勢いが落ちている。いずれも FastAPI を上回る点が無い |

## 可逆性

| 項目 | 内容 |
| --- | --- |
| 後から変えられるか | 変えられる |
| 変えるとしたら必要なこと | ルーティングと入出力のモデルを書き換える。業務の処理(`storage`・`trash` など)はフレームワークに依存させないため、`src/filetto/api/**` に閉じる。Starlette + Pydantic へは同じ土台の上で機能を減らす形で移せる |
| いつまでなら安く変えられるか | API の経路が少ないうち(F-001 の WebUI の経路が揃う前) |

## 非機能への影響

| 項目 | 影響 |
| --- | --- |
| 性能 | 差は小さい。ボトルネックは OCR・パースの計算量 |
| 可用性 | 影響なし |
| セキュリティ | Starlette の勧告(multipart・Range・StaticFiles など、2024〜2026 年に 8 件)を受ける。どのフレームワークでも MCP SDK 経由で Starlette は入る |
| 運用 | 版の固定を上げる作業が定期的に要る |

## 事業への影響

| 項目 | 内容 |
| --- | --- |
| 影響を受ける利用者・業務 | Filetto を WebUI から使う利用者。版を上げた際の挙動の変化で API が壊れる |
| 顕在化が分かる兆候 | 版を上げる変更で OpenAPI スキーマや API の検査が変わる。FastAPI の保守が止まる |
| 回復に要する時間 | 1〜5 日(版を戻す、または Starlette + Pydantic へ移す) |
| 取り消しの可否 | 人手で戻せる |
| 影響する必達基準 | 該当なし |

## 影響

- REST と MCP を1つの ASGI アプリに置ける(SDK の `streamable_http_app()` をマウントする)
- 0.x の変更を版の固定で抑える。版を上げるたびに互換性の確認が要る
- この決定で解決しないこと: OpenAPI スキーマの差分テスト(版を上げる変更の前に足す)、MCP のマウントの細部(Task-3 で決める)

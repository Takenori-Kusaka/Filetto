---
id: S0-005
stage: S0 探索
issue: "#4"
status: 判定済み
verdict: 条件つきで採用できる
date: 2026-08-12
---

# S0-005 Lore(Epic Games)を VersionStore 実装として初版から採用できるか

Issue #4 の検証記録です。基準1〜5 をすべて判定しました。時間箱内に収まっています。

> **文書 ID について**: Issue の成果物指定は `docs/spikes/S0-002-lore.md` でしたが、`S0-002` は既に `S0-002-alternatives.md`(対案の比較)で使用済みです。ID の重複を避けるため `S0-005` を採番しました。**この変更は Dev の判断です。** 別の採番を希望される場合はご指示ください。

## 結論

**条件つきで採用できます。** 基準1〜5 はすべて満たしました。

ただし、Issue の前提にあった「ライブラリとして組み込める」は成立しません。**Lore はサーバプロセスの常駐を要求します。** これを受け入れられるなら、内容アドレス方式・重複排除・破損検出のいずれも実測で期待どおりに動作しました。

| # | 基準 | 判定 |
| --- | --- | --- |
| 1 | TS または Go の SDK から 登録・取得・履歴一覧・バージョン削除の4操作 | **満たす** |
| 2 | 追加コンテナ 1 個以下、またはライブラリ組み込み | **満たす**(公式 Dockerfile で 1 コンテナ。ライブラリ単体では不可) |
| 3 | 10MB PDF の末尾を変えた 10 版が単純加算の 30% 以下 | **満たす(9.6%)** |
| 4 | 破損時に沈黙して誤ったデータを返さない | **満たす** |
| 5 | 破壊的変更の予告または保管形式の互換性に関する記述 | **記述あり** |

## 実行環境

| 項目 | 値 |
| --- | --- |
| OS | Windows 11 Pro 10.0.26200 |
| Lore CLI | `lore 0.8.6+373`(公式リリースの `lore-v0.8.6-x86_64-pc-windows-msvc.zip`) |
| Lore Server | `loreserver 0.8.6+373`(同 `loreserver-v0.8.6-x86_64-pc-windows-msvc.zip`) |
| SDK | `@lore-vcs/sdk`(JavaScript / TypeScript SDK、npm) |
| ライセンス | **MIT**(本体・JS SDK・Go SDK いずれも) |
| リポジトリ | [EpicGames/lore](https://github.com/EpicGames/lore) 8,375 stars / Rust / 最終更新 2026-08-11 |

システムインストールは行わず、ZIP を展開して検証用ディレクトリから実行しました。

## 基準1: SDK から4操作が実行できるか — 満たす

**JavaScript / TypeScript SDK(`@lore-vcs/sdk`)から 4 操作すべてを実行できました。**

| 操作 | 使用した API | 結果 |
| --- | --- | --- |
| 登録(コミット相当) | `fileStage` → `revisionCommit` | **成功**。リビジョン 12・13・14 を SDK から作成 |
| 旧版の取得(復元相当) | `fileWrite`(`path` + `revision` + `output`) | **成功**。v1 の内容 `"SDK registration test v1\n"` を取り出した(現在の内容は v3) |
| 履歴の一覧 | `revisionHistory` | **成功**。14 リビジョンを列挙。`revisionHistoryEntry` イベントに署名・番号・親が入る |
| 特定バージョンの削除 | `fileObliterate` | **成功**。`fileObliterate` / `fileStageFile` / `complete` イベントが返る |

実際の出力です。

```
[OK]   fileStage (登録)  events=7
[OK]   revisionCommit (登録)  events=10
[OK]   revisionHistory (履歴一覧)  events=59
       revisions: 14  最新=#14  最古=#1
[OK]   fileWrite (旧版の取得)  events=3
       復元された内容: "SDK registration test v1\n"
       現在の内容    : "SDK registration test v3 (this is the newest)\n"
[OK]   fileObliterate (バージョン削除)  events=4
```

### 落とし穴: 実行されていないのに成功に見える

**SDK の fluent API は `.waitAsync()` または `.collectAsync()` を呼ぶまで何も実行しません。**

```javascript
// 誤り: 何も起きないが、例外も出ず成功したように見える
await lore.revisionCommit(g, { message: "..." }).callback(cb);

// 正しい
await lore.revisionCommit(g, { message: "..." }).callback(cb).waitAsync();
```

`.callback()` は `LoreFluentApi` を返すだけで Promise ではありません。`await` すると即座にそのオブジェクトが返り、**戻り値は `{}`、イベントは 0 件、リポジトリは無変更**になります。本検証でも最初はこれに気づかず、8 操作すべてが「成功」と表示されながらリビジョンが 1 つも増えていませんでした。

Filetto で採用する場合、**この呼び出し忘れを型か lint で検出できるようにしてください。** 沈黙する失敗は基準4 の思想に反します。

引数名にも注意が必要でした。`revisionCommit` は `message`(`description` ではない)、`fileWrite` は `output`(`outputPath` ではない)、`fileObliterate` は `path` 単数(`paths` ではない)、`fileWrite` の `revision` はリビジョン番号ではなく**署名ハッシュ**です。誤った引数は無視され、`file not found: `(パスが空)のようなメッセージになります。

## 基準2: 追加コンテナ 1 個以下、またはライブラリ組み込み — 満たす

**ライブラリ単体では成立しません。サーバプロセスが必須です。**

- `lore repository create` は `lore://HOST:PORT/NAME` 形式の URL を要求します
- 公式のクイックスタートも「install Lore and start a local server in demo mode」で、ローカル利用でも `loreserver` を起動します
- 実測でも、`loreserver` を起動して `http://127.0.0.1:41339/health_check` が 200 を返してからでないとリポジトリを作成できませんでした

**一方、追加コンテナは 1 個で済みます。** 公式の `lore-server/Dockerfile` が存在します。

```dockerfile
FROM debian:trixie-slim
COPY --from=builder /build/loreserver-bin /usr/local/bin/loreserver
RUN cat <<'EOF' > /etc/lore/config/docker.toml
[immutable_store.local]
path = "/data"

[mutable_store.local]
path = "/data"
EOF
ENV LORE_CONFIG_PATH=/etc/lore/config
ENV LORE_ENV=docker
```

`/data` をボリュームにすれば永続化できます。**`docker compose` へ 1 コンテナ追加で成立します。**

公開ポートは 2 つです。

| ポート | プロトコル | 用途 |
| --- | --- | --- |
| 41337 | **QUIC(UDP)** および gRPC | クライアント接続の主経路 |
| 41339 | HTTP | ヘルスチェック等 |

### ローカルファイルシステムで完結するか — します

保管領域は既定で完全にローカルです。`lore-server/config/default.toml` の記述です。

```toml
[immutable_store]
mode = "local"

[mutable_store]
mode = "local"

# `path` is intentionally omitted: when unset, the server derives a path under
# the system temporary directory (`<tmp>/lore-server`) at startup.
```

実測でも、すべてのデータが `%TEMP%/lore-server/{immutable,mutable}` 配下の packfile として置かれました。**外部サービスへの接続は一切発生していません。** 永続運用では `path` を明示指定します(既定は一時ディレクトリなので、そのままでは消えます)。

### コンテナ / AWS Lambda 上での運用について

**コンテナ: 問題ありません。** 上記の公式 Dockerfile がそのまま使えます。ストアは `/data` ボリューム、あるいは後述の AWS モードです。

**AWS Lambda: 現状は適しません。** 理由は 3 つです。

1. **主エンドポイントが QUIC(UDP 41337)です。** Lambda には UDP のインバウンドがありません。Function URL も API Gateway も HTTP のみで、QUIC を終端できません
2. **常駐リスナ前提の設計です。** `num_listeners = 10`、`keep_alive = 500`、`idle_timeout = 30_000` といった設定が既定で、リクエスト駆動・最大 15 分の実行モデルとは噛み合いません。microVM で起動が速くても、この 2 点は実行環境の速度では解消しません
3. **ストアの既定がローカル FS です。** Lambda の `/tmp` は揮発するため、そのままでは保管領域になりません

ただし**永続ストアを AWS に置くことは可能**です。`lore-server` は `lore-aws` クレートに依存し、`lore-aws/src/store/immutable_store.rs` が **S3 + DynamoDB** 実装を持ちます。設定側も `mode = "aws"` を受け付けます(`lore-server/src/settings.rs` に該当のテストがあります)。

したがって現実的な構成は次になります。

| 構成 | 可否 |
| --- | --- |
| ローカルのプロセス常駐 + ローカル FS | **可**(本検証で実測) |
| Docker / docker compose + ボリューム | **可**(公式 Dockerfile) |
| ECS / Fargate / EC2 + S3 + DynamoDB | **可**(`mode = "aws"`。本検証では未実測) |
| AWS Lambda | **不可**(UDP インバウンド不在・常駐モデル不一致) |

なお、出荷される設定プロファイルは `default.toml` / `local.toml` / `dev-local.toml` / `gha.toml` のみで、**AWS 用のサンプル設定は同梱されていません**。採用する場合は自前で書く必要があります。

## 基準3: 重複排除 — 満たす(9.6%)

### 測定対象(測定前に確定)

コーパスの PDF 12 件を結合した **8,925,828 バイト(8.51MB)の PDF 1 件**です(`make_pdf.py` で生成)。Issue の指定は「10MB 程度」で、コーパスの PDF をすべて使い切って 8.51MB になりました。**測定後にファイルを選び直してはいません。**

各版は**末尾にコメント行を 102 バイト追記**しただけで、それ以外は変更していません。

### 結果

| 版 | ファイルサイズ | サーバ保管領域 |
| --- | --- | --- |
| 1 | 8,925,828 | 8,167,896 |
| 2 | 8,925,930 | 8,207,931 |
| 3 | 8,926,032 | 8,247,959 |
| 5 | 8,926,236 | 8,342,160 |
| 10 | 8,926,746 | **8,546,324** |

```
単純加算(10版) = 89,258,280 bytes
サーバ保管領域  =  8,546,324 bytes
```

**9.6%。基準の 30% 以下を大きく下回ります。** 1 版増えるごとの増分は約 40,000 バイトで、追記した 102 バイトに対しては大きいものの、8.5MB の再保存に比べれば 0.45% です。

なお、作業ディレクトリ側の `.lore` は **86,654 バイト**にしか増えていません。実体はサーバの保管領域にあり、クライアント側はメタデータのみを保持します。

### 同一内容の別ファイル(手順5)

同じ 8.51MB の PDF を別名で 3 つ追加してコミットしました。

```
before: server=8,556,492
after (同一内容3ファイル追加): server=8,557,364
単純加算なら +26,777,484 bytes 増えるはず
```

**増分 872 バイト。** 内容アドレス方式が想定どおり働いています。

## 基準4: 破損時に沈黙して誤ったデータを返さないか — 満たす

**2 通りの壊し方を試し、どちらも明示的なエラーになりました。誤ったデータは返りません。**

作業ディレクトリのキャッシュに残っていると破損が見えないため、**ローカルキャッシュを持たない新規クローン**で読み出しています。

### ケースA: 保管領域の packfile を 1 つ削除

| 結果 | |
| --- | --- |
| クローンの終了コード | **17**(非ゼロ) |
| 生成物 | `big.pdf.~loretemp`(8,926,746 バイト)のみ。**`big.pdf` は作られない** |
| 内容の誤り | なし(正規のファイル名で提示されない) |

### ケースB: packfile の中身を 256 バイト反転(ハッシュ不一致)

同じく終了コード **17**、生成物は `.~loretemp` のみでした。エラーメッセージです。

```
Cloned 1/2 files (14.00 bytes/8.51 MiB)
Clone complete in 2.03s
[Error] Not connected to remote: get: Failed sending command: Server returned error code 3
  at lore-storage\src\error.rs:35:9
  at lore-revision\src\immutable.rs:280 - reading immutable data
  at lore-revision\src\repository\clone.rs:1957 - Failed to clone file .../big.pdf
```

**どのファイルの読み出しで失敗したかが明示されます。** 可逆性のための仕組みとして、この挙動は要求を満たします。

### ただし 2 つの問題があります

1. **`repository verify` はサーバ側の破損を検出しません。** 保管領域を壊した状態でも `Verified repository state integrity` を返し、終了コードは 0 でした。これはローカルのリポジトリ状態を検証するコマンドであって、サーバ保管領域の健全性検査ではありません
2. **修復手段が見当たりません。** CLI に `repository verify` / `repository gc` はありますが、破損した packfile を検出して隔離・再取得する経路はドキュメント・CLI ヘルプのいずれにも見当たりませんでした
3. **`.~loretemp` が残ります。** 8.9MB の一時ファイルが作業ディレクトリに残置されました。自動では消えません

Filetto が採用する場合、**サーバ側保管領域の定期検証と `.~loretemp` の掃除は Filetto 側の責務**になります。

## 基準5: 破壊的変更・保管形式の互換性に関する記述 — あり

**3 か所に明示的な記述がありました。**

`docs/roadmap.md`:

> Lore ships today as a pre-stable 0.x: **the formats are built to last — content you commit now stays readable by every future release** — but APIs and protocols can still change before 1.0, when strict backward compatibility takes over.

`docs/faq.md`:

> Lore is launching as a pre-stable 0.x release, meaning **APIs and protocols may still evolve before we reach a 1.0 stable release** — at which point strict backward compatibility will apply.

システム設計ドキュメント(§6.7):

> Lore is not yet at 1.0. Until it gets there, pre-1.0 semantic-versioning conventions apply — **formats and protocols may still change in incompatible ways between minor revisions**. ... **a newer version of the library can always read what an older version has written.** Data committed to a Lore repository today remains readable by every future Lore release.

加えて、**on-disk format の変更は Lore Enhancement Proposal(LEP)を通す**と CONTRIBUTING に定められています。

> Changes to the wire protocol, on-disk format, or public APIs go through a Lore Enhancement Proposal — the place where the biggest roadmap items get designed in public.

### この記述の読み方

**「今書いたデータが将来読めなくなる」リスクは、明示的に否定されています。** これは Filetto にとって最も重要な点で、可逆性の担保を外部実装に預ける判断を支えます。

一方で **API とプロトコルは 0.x の間に非互換に変わりえます**。Filetto 側のコードは書き直しが発生しうる、ということです。`context/standards/extensibility.md` の方針どおり、**VersionStore 境界の背後に置くこと**が前提になります。

なお UEFN との互換性については、圧縮形式が Oodle から Zstandard へ移行中で、現時点では相互運用できないと明記されています。Filetto には影響しません。

## 想定外だった挙動

1. **SDK の fluent API が `.waitAsync()` なしでは沈黙して何もしない**(前述)。最も危険な落とし穴です
2. **`repository create` に URL が必須**で、ローカル限定のリポジトリを作る経路が見当たりませんでした
3. **既定の保管パスがシステム一時ディレクトリ**(`%TEMP%/lore-server`)です。設定なしで運用するとデータが消えます
4. **サーバ稼働中は packfile を削除・変更できません**(`Device or resource busy`)。検証ではサーバを停止してから壊しました
5. **`repository verify` の対象範囲が狭い**(前述)

## 結論と、採用の条件

**条件つきで採用できます。** 次の 4 点を Filetto 側で引き受けるなら、初版から `VersionStore` の実装として使えます。

| # | 条件 |
| --- | --- |
| 1 | **`loreserver` の常駐を受け入れる。** `docker compose` に 1 コンテナ追加、または配布物に同梱して子プロセスとして起動する |
| 2 | **保管パスを明示設定する。** 既定のままではシステム一時ディレクトリに置かれ、消える |
| 3 | **サーバ側保管領域の定期検証と `.~loretemp` の掃除を Filetto 側で持つ。** Lore には修復コマンドがない |
| 4 | **`VersionStore` 境界の背後に置く。** 0.x の間は API とプロトコルが非互換に変わりうる(保管形式の前方互換は約束されている) |

条件1 を受け入れられない場合(ライブラリ単体で完結させたい場合)、**Lore は採用できません**。その場合は ADR-0003 の自前 CAS を維持し、再評価の条件を「v1.0 到達時」ではなく **「サーバ常駐なしのローカル専用モードが提供されたとき」** に書き換えるべきです。

## 検証していないこと

- **Go SDK**。JS/TS SDK で 4 操作すべてを確認できたため、Issue の「TypeScript または Go」を満たすと判断しました
- **`mode = "aws"` の実動作**。設定とコードの存在は確認しましたが、S3/DynamoDB での稼働は未実測です
- **Docker イメージのビルドと起動時間**。Dockerfile は Rust のソースビルドを行うため、時間箱内に収まらないと判断しました。イメージサイズと起動時間は未実測です
- **アドバイザリロックの実挙動**。Issue の懸念に挙がっていましたが、単一利用者の想定では優先度が低いと判断しました
- **大量ファイル・長期運用時の挙動**

## 再現手順

```bash
# バイナリ取得(システムインストールなし)
gh release download v0.8.6 -R EpicGames/lore \
  -p "lore-v0.8.6-x86_64-pc-windows-msvc.zip" -p "loreserver-v0.8.6-x86_64-pc-windows-msvc.zip"
unzip -o -q lore-*.zip -d bin && unzip -o -q loreserver-*.zip -d bin

# サーバ起動(ローカル完結)
./bin/loreserver.exe &
curl -i http://127.0.0.1:41339/health_check   # 200 を待つ

# リポジトリ作成とコミット
mkdir -p work/proj1 && cd work/proj1
../../bin/lore.exe repository create "lore://127.0.0.1:41337/filetto-spike"
../../bin/lore.exe stage <file> && ../../bin/lore.exe commit "msg" && ../../bin/lore.exe push

# SDK
npm install @lore-vcs/sdk
# 呼び出しは必ず .waitAsync() / .collectAsync() で終える
```

## ADR への反映(判定後の扱い)

Issue の指定どおり、いずれの結果でも ADR-0003 の改訂が発生します。本検証は「**条件つきで採用できる**」でしたので、**PO が上記の条件1〜4 を受け入れるか**を判断したうえで、次のいずれかになります。

- 受け入れる → ADR-0003 を改訂し、`VersionStore` の初版実装を Lore に切り替える。条件1〜4 を ADR の「結果」に明記する
- 受け入れない → ADR-0003 は自前 CAS を維持し、再評価の条件を「サーバ常駐なしのローカル専用モードが提供されたとき」へ書き換える

## 関連

- Issue #4
- ADR-0003: `context/decisions/0003-reversible-file-operations.md`
- 設計標準: `context/standards/extensibility.md`
- [EpicGames/lore](https://github.com/EpicGames/lore) — MIT
- [Lore JavaScript SDK](https://github.com/EpicGames/lore-js) — MIT
- [Lore Go SDK](https://github.com/EpicGames/lore-go) — MIT

---
id: S0-015
stage: S0 探索(S1 の途中で生じた技術検証)
issue: "PR #188(ADR-0004 案H)"
status: 実測済み
verdict: AWS 上で成立する。ただし Lambda の標準ランタイムでは動かず、コンテナイメージ方式の Lambda に限る。転送の単位が Lore の pack ファイルになるため版ごとの転送量は原本の 4〜12%、競合は S3 の If-Match で検出でき、負けた側は保管を捨てて回復する
date: 2026-10-29
---

# S0-015 Lambda 内のオフライン Lore + S3 の目録(案H)が AWS 上で成立するかの実測

ADR-0004(PR [#188](https://github.com/Takenori-Kusaka/Filetto/pull/188))の案H は「手元の模擬で成立、AWS 上は未検証」でした。本記録は**実際の AWS アカウント(ap-northeast-1)に Lambda と S3 を作って動かした結果**です。ドキュメントの読解で代替した項目はありません。

**本記録は成立の可否と実測値だけを示します。案H を採るかの判断(G-3)は技術判断者が行い、ADR-0004 の「採らなかった理由」の記入も人が行います。**

## 結論

| # | 確かめたこと | 判定 |
| --- | --- | --- |
| 1 | Lambda で `lore-vcs` 0.11 のオフライン保管が動く | **条件つきで動く**。標準ランタイム(Amazon Linux 2023、glibc 2.34)では動かない。コンテナイメージ方式(glibc 2.39 以上の基盤)なら x86_64・arm64 とも動く |
| 2 | `repository_flush` の後に `.lore` の差分を S3 へ写し、`/tmp` を失った別の実行環境から全版を取り出せる | **成立**。x86_64 で 10 版、arm64 で 3 版、作業ファイルを写さない方式で 5 版。取り出した内容の SHA-256 が保存時と一致 |
| 3 | 同時に 2 つの実行環境が保存したとき、目録の If-Match で競合を検出し、負けた側が回復する | **成立**。3 回とも片方だけが 412 になり、負けた側は `/tmp` を捨てて次の呼び出しで目録に追随。版の番号に欠落も重複もない |
| 4 | 使っていない間の費用が保管料だけになる | **成立**。VPC・NAT・常時起動の資源なし。月額は S3 の保管料($0.025/GB)と ECR のイメージ保管($0.10/GB、イメージ 82MB)だけ |
| 5 | 冷えた起動の時間 | 17MB の保管で **3.5 秒**(Init 0.8 秒 + Lore の初期化 1.6 秒 + 取り込み 1.6 秒)。保管が大きくなると取り込みが線形に伸びる(17MB で約 10MB/秒。それ以上は未測定) |

## 実行環境

| 項目 | 値 |
| --- | --- |
| AWS アカウント / リージョン | `443370718249` / `ap-northeast-1` |
| Lambda | コンテナイメージ方式、メモリ 2048MB、一時ストレージ 2048MB、タイムアウト 300 秒。関数 `filetto-lore-feasibility-x86`(x86_64)と `filetto-lore-feasibility-arm64`(arm64) |
| イメージの基盤 | `public.ecr.aws/docker/library/python:3.13-slim-trixie`(Debian 13、glibc 2.41、Python 3.13.18)+ `awslambdaric` + `boto3` + `lore-vcs==0.11.0`。イメージ 82MB |
| S3 | バケット 1 つ。目録 `manifest.json` と `objects/<sha256>` |
| `lore-vcs` | 0.11.0(`lore_vcs-0.11.0-py3-none-manylinux_2_39_{x86_64,aarch64}.whl`) |
| 手元 | Windows 11、Docker Desktop 29.6.2、AWS CLI 2.34.10 |

検証用のコードは [`S0-015-scripts/`](./S0-015-scripts/) にあります(`handler.py` が Lambda の本体、`Dockerfile`、`inv.sh` が呼び出し、`local_probe.py` が手元の模擬)。

## 検証1: 標準ランタイムでは動かない。コンテナイメージ方式なら動く

`lore-vcs` の Linux 用ホイールは `manylinux_2_39` で、同梱の `lorelib-amd64-unknown-linux.so`(38MB)は **glibc 2.39 のシンボル `pidfd_spawnp` と `pidfd_getpid`** を要求します(ELF の `.gnu.version_r` を読んで確認。arm64 の `lorelib-arm64-graviton-linux.so` も同じ)。Lambda の標準ランタイム(Python 3.13、Amazon Linux 2023)の glibc は 2.34 のため、zip 配置では読み込めません。

glibc 2.41 の Debian trixie を基盤にしたコンテナイメージで、x86_64・arm64 とも読み込みと全操作が動きました。

| 項目 | x86_64 | arm64 |
| --- | --- | --- |
| `info`(glibc) | `glibc 2.41`、Python 3.13.18 | 同左 |
| Init(イメージの初期化) | 0.8〜1.9 秒 | 3.0 秒(初回) |
| Lore の初回の初期化(`repository_create` を含む最初の呼び出し) | 1.6〜3.8 秒 | 4.4 秒 |

もう 1 つの条件があります。**Lore は起動時に `$HOME/.config/lore` を作ります**。Lambda では `/tmp` 以外が読み取り専用のため、最初の試行は `loading global config: Read-only file system (os error 30)` で失敗しました。`HOME` と `XDG_CONFIG_HOME` を `/tmp` の下へ向けて解消しました。

## 検証2: 往復(保存 → flush → S3 → 別の実行環境で復元)

手順は ADR-0004 の案H のとおりです。`save` は原本を書いて `file_stage` → `revision_commit` → `repository_flush` の後、リポジトリの下の全ファイルを SHA-256 で名前づけし、変わったものだけを `objects/<sha>` へ `If-None-Match: *` で置き、目録を `If-Match: <前の ETag>` で進めます。`reset` は `/tmp` を消して冷えた起動を模します。`versions` と `read` は目録を読み、手元と違うファイルだけを取り込んでから Lore を呼びます。

### x86_64、8.5MB の原本を 5 版(各版は末尾 64 バイトだけ違う。S0-005 と同じ形)

| 版 | Lore の保存 | flush | S3 へ写す | 写したオブジェクト | 写したバイト | うち `.lore` の差分 |
| --- | --- | --- | --- | --- | --- | --- |
| 1(冷えた起動) | 663ms | 59ms | 1,000ms | 206 | 17.0MB | 8.5MB |
| 2 | 50ms | 18ms | 328ms | 38 | 9.1MB | 642KB |
| 3 | 46ms | 9ms | 410ms | 36 | 8.9MB | 444KB |
| 4 | 43ms | 7ms | 341ms | 34 | 9.5MB | 1,018KB |
| 5 | 41ms | 2ms | 397ms | 34 | 8.8MB | 326KB |

「写したバイト」の大半は作業ファイル(原本の写し、8.5MB)の再送です。これは検証6 で除けることを確かめました。

### 復元

| 操作 | 結果 |
| --- | --- |
| `reset` → `versions` | 467 オブジェクト(17.2MB)を 1.6 秒で取り込み、版 1〜7 を列挙 |
| `read` 版 2 | SHA-256 が保存時の値と一致(`49e012c8…`、2MB の試行)/(`1b50e49f…`、8.5MB の試行) |
| `read` 版 4 | SHA-256 が一致 |

arm64 でも同じ手順(8.5MB × 3 版 → `reset` → `read` 版 2)で、372 オブジェクト(17.1MB)を 0.98 秒で取り込み、SHA-256 が一致しました。

## 検証3: 重複排除の効き(転送の単位が pack ファイルになる)

S0-005 では、`loreserver` の保管領域は 8.5MB の原本に末尾の変更を加えた版 1 つにつき約 40KB 増えました。案H では、Lore のオフライン保管を**ファイルの粒度**で S3 へ写すため、追記された pack ファイル(`.lore/immutable/index/<xx>/pack/1`)は**ファイル全体**が送り直されます。実測の `.lore` の差分は版ごとに **326KB〜1,018KB(原本の 3.8〜12%)** で、S0-005 の 40KB より 8〜25 倍大きい一方、原本を丸ごと置き直す場合(8.5MB)の 1/8〜1/26 です。

1 版あたりに写すオブジェクトは 34〜38 個です(pack と index の対)。S3 の PUT は 1,000 件 $0.0047 なので、版 1 つの PUT 料金は約 $0.00017 です。

## 検証4: 同時書き込みの競合

予約同時実行数は設定できませんでした(後述)。そのため、**温まった 2 つの実行環境から同時に `save` を投げる**本物の競合を 3 回起こしました。

| 回 | 勝った側 | 負けた側 |
| --- | --- | --- |
| 1 | 版 8 を保存、目録 seq 7 → 8 | Lore は版 8 を作ったが目録の書き込みが **412 PreconditionFailed**。`/tmp` を捨てた |
| 2 | 版 9、seq 8 → 9 | 412、`/tmp` を捨てた |
| 3 | 版 10、seq 9 → 10 | 412、`/tmp` を捨てた |

直後の `versions` は 1〜10 を欠落も重複もなく返し、目録の seq は 10 でした。

**負けた側が `/tmp` を捨てるのは必須です。** 手元の模擬で、捨てずに次の保存へ進むと、目録に無いコミット(競合で負けた版)が次の保存に混入し、版の番号が 1 つずれました(目録では版 3 が無いのに Lore は版 4 を作る)。`handler.py` は 412 を受けたら保管を消し、次の呼び出しで目録から取り直します。

### 予約同時実行数 1 は、このアカウントでは設定できない

```
aws: [ERROR]: An error occurred (InvalidParameterValueException) when calling the PutFunctionConcurrency operation:
Specified ReservedConcurrentExecutions for function decreases account's UnreservedConcurrentExecution below its minimum value of [10].
```

アカウントの Lambda の同時実行数の上限が 10(新しいアカウントの既定)で、予約すると未予約分が 10 を下回るためです。上限を 11 以上へ引き上げる申請(Service Quotas)が要ります。**正しさは目録の If-Match が守る**ので、予約同時実行数は「負けた側の無駄な実行を減らす」ための装置であり、成立の条件ではありません。

## 検証5: 冷えた起動

環境変数を変えて実行環境を新しくし、17MB(467 オブジェクト)の保管に対して `versions` を呼びました。

| 区間 | 時間 |
| --- | --- |
| Init(イメージの起動と `import`) | 818ms |
| Lore の初回の初期化(`repository_create` 相当の最初の呼び出し) | 1,571ms |
| 目録を読み 467 オブジェクトを 16 並列で取り込む | 1,631ms |
| `file_history` | 278ms |
| 合計 | 3,480ms(課金 4,301ms) |

取り込みは小さなファイルが多く(1 オブジェクト平均 37KB)、約 10MB/秒でした。保管が 1GB なら取り込みだけで 100 秒前後、`/tmp` の上限 10GB に近づくと Lambda のタイムアウト(15 分)に届く計算になります。**17MB を超える大きさは測っていません。**

## 検証6: S3 の肥大化と、作業ファイルを写さない方式

案H は内容のハッシュ名でオブジェクトを置くため、**目録から外れた古いオブジェクトは残り続けます**(孤児)。

| 方式 | 版の数 | 目録が指すバイト | 置かれた全オブジェクト | 孤児 |
| --- | --- | --- | --- | --- |
| 作業ファイルも写す | 7 | 17.2MB | 71.1MB(418 個) | 53.9MB。原本の写し(8.5MB)が版ごとに新しいオブジェクトになるため |
| `.lore` だけ写す | 5 | 8.6MB | 10.3MB(350 個) | 1.6MB(16%)。追記で置き換わった pack の古い版 |

作業ファイル(原本の写し)を写さなくても、`file_history` と `file_write`(旧版の取り出し)は動きます。手元(Windows)で `.lore` だけを複製した先から全版を取り出せることを確かめ、Lambda(x86_64、`SYNC_LORE_ONLY=1`)でも 5 版を保存 → `reset` → 版 2 と版 5 の SHA-256 が一致しました。この方式では版 1 つの転送が **360〜540KB** です。

孤児は目録に無いオブジェクトを消す掃除(書き込みが 1 系統なので安全)で回収できます。本検証では実装していません。

## 費用の見積もり

単価は 2026-10-29 に AWS Price List API(`aws pricing get-products`、ap-northeast-1)から取った値です。請求前に人が確かめてください。

| 項目 | 単価 |
| --- | --- |
| S3 Standard 保管 | $0.025 / GB-月(50TB まで) |
| S3 PUT | $0.0047 / 1,000 件 |
| S3 GET | $0.00037 / 1,000 件 |
| Lambda 実行時間(x86_64 / arm64) | $0.0000166667 / $0.0000133334 per GB-秒 |
| Lambda 呼び出し | $0.20 / 100 万件 |
| Lambda 一時ストレージ(512MB 超過分) | $0.000000037 / GB-秒 |
| ECR 保管 | $0.10 / GB-月 |

| 場面 | 見積もり |
| --- | --- |
| **使っていない月**(保管 5GB) | S3 $0.125 + ECR(82MB)$0.008 = **約 $0.13 / 月**。VPC・NAT・常時起動の資源はなし |
| 使っていない月(保管 50GB) | 約 $1.26 / 月 |
| 保存 1 回(温まった実行環境、8.5MB、`.lore` だけ写す) | Lambda 0.4 秒 × 2GB = $0.000013、PUT 36 件 = $0.00017、合計 **約 $0.0002**。1,000 回で約 $0.19 |
| 冷えた起動 1 回(保管 17MB) | GET 467 件 = $0.00017、Lambda 3.5 秒 × 2GB = $0.00012、合計約 $0.0003 |

費用は PUT の件数(版 1 つに 34〜38 個)が支配します。保管量が増えても孤児の掃除をすれば保管料は Lore の保管と同じ比率で増えます。

## 案H を採る場合に Filetto 側が引き受けること

| # | 事項 | 根拠 |
| --- | --- | --- |
| 1 | **コンテナイメージ方式の Lambda**にし、基盤を glibc 2.39 以上にする(zip 配置は不可) | 検証1 |
| 2 | `HOME`(または `XDG_CONFIG_HOME`)を `/tmp` の下へ向ける | 検証1 |
| 3 | 書き込みの手順を「flush → 差分を `If-None-Match: *` で置く → 目録を `If-Match` で進める」に固定し、**412 を受けたら `/tmp` の保管を捨てる** | 検証2・4 |
| 4 | 作業ファイル(原本の写し)を目録に含めない | 検証6 |
| 5 | 目録に無いオブジェクトを消す掃除を持つ | 検証6 |
| 6 | 予約同時実行数 1 を使うなら、同時実行数の上限を 11 以上へ引き上げる申請をする | 検証4 |
| 7 | 保管の大きさに上限(`/tmp` の 10GB より十分小さい値)を置き、冷えた起動の時間を監視する | 検証5 |
| 8 | 「flush の後に写せば別の環境で開ける」は Lore の公開された仕様ではない。`lore-vcs` を上げるたびに本記録の往復を再実行する | ADR-0004 |

## 検証していないこと

- 17MB を超える保管での取り込みの時間と、pack ファイルが大きくなったときの版ごとの転送量
- 孤児の掃除の実装と、掃除と読み出しが重なったときの挙動
- 保管が壊れたとき(オブジェクトの欠落・改変)に Lore が誤った内容を返さないこと。S0-005 の結果(終了コード非ゼロで `.~loretemp` が残る)が Lambda でも同じかは未確認。`handler.py` は取り込み時に SHA-256 を照合して欠落・改変を検出する
- 実行環境が `/tmp` を保ったまま目録だけ進んだとき(別の実行環境が書いた後)に、Lore が手元の状態を正しく読み替えること。本検証の `pull` はファイル単位で上書きし、競合した側は捨てるため、この経路は競合の回で間接的にだけ通っている
- Lambda Function URL / API Gateway からの呼び出し、認証、F-001 の API 層との結線
- `lore-vcs` 0.12.0(2026-10 時点の最新)

## 再現手順

```bash
# 1. イメージを作って ECR へ置く(Docker Desktop が要る。単一アーキテクチャのマニフェストにする)
cd docs/spikes/S0-015-scripts
docker build --platform linux/amd64 --provenance=false --sbom=false -t filetto-lore-feasibility:x86 .
aws ecr get-login-password | docker login --username AWS --password-stdin <ACCOUNT>.dkr.ecr.ap-northeast-1.amazonaws.com
docker tag filetto-lore-feasibility:x86 <ACCOUNT>.dkr.ecr.ap-northeast-1.amazonaws.com/filetto-lore-feasibility:x86
docker push <ACCOUNT>.dkr.ecr.ap-northeast-1.amazonaws.com/filetto-lore-feasibility:x86

# 2. 関数を作る(ロールは AWSLambdaBasicExecutionRole + 対象バケットの s3:GetObject/PutObject/DeleteObject/ListBucket)
aws lambda create-function --function-name filetto-lore-feasibility-x86 --package-type Image \
  --code ImageUri=<ECR の URI>@<digest> --role <ロールの ARN> --architectures x86_64 \
  --memory-size 2048 --ephemeral-storage Size=2048 --timeout 300 \
  --environment "Variables={BUCKET=<バケット>,PREFIX=x86/,SYNC_LORE_ONLY=1}"

# 3. 呼び出す(inv.sh は応答と REPORT 行を出す)
./inv.sh filetto-lore-feasibility-x86 '{"op":"info"}'
./inv.sh filetto-lore-feasibility-x86 '{"op":"save","path":"docs/a.pdf","gen_bytes":8500000,"seed":"1"}'
./inv.sh filetto-lore-feasibility-x86 '{"op":"reset"}'
./inv.sh filetto-lore-feasibility-x86 '{"op":"read","path":"docs/a.pdf","version":"1"}'
./inv.sh filetto-lore-feasibility-x86 '{"op":"stale_push","path":"docs/a.pdf","gen_bytes":1000,"seed":"9"}'   # 412 になる
```

手元の模擬(`local_probe.py`)は Windows 用のホイールで、`.lore` の変化と flush 後の複製可否を確かめます。

## 関連

- ADR-0004(PR [#188](https://github.com/Takenori-Kusaka/Filetto/pull/188))案H
- [S0-005](./S0-005-lore.md)(`loreserver` での重複排除 9.6%、Lambda は「不可」とした当時の判断。本記録はオフライン保管 + コンテナイメージ方式で前提が変わったことを示す)
- 仕様 [`specs/F-001/spec.md`](../../specs/F-001/spec.md) 前提1・受入基準15〜22
- 実装 `src/filetto/version/lore_store.py`(Task-8。`handler.py` の `LoreStore` はこれを写したもの)
- [lore-vcs on PyPI](https://pypi.org/project/lore-vcs/) / [AWS Lambda の Python 3.13 ランタイムは AL2023(glibc 2.34)](https://aws.amazon.com/blogs/compute/python-3-13-runtime-now-available-in-aws-lambda/) / [Lore System Design](https://epicgames.github.io/lore/explanation/system-design/)

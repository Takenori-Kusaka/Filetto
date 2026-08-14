# PL-0007: pr-base-check が「いまの本文」を読むようにする

対象 Issue: [#119](https://github.com/Takenori-Kusaka/Filetto/issues/119)
作成: 2026-08-14 / レーン: Platform

## 1. 採った案

**案C(スクリプトが本文を GitHub API から取り直す)を採りました。** あわせて、**落ちたときに再実行の手順を出力へ含めます。**

PO は A か B を妥当とし、C は「検査を通すために検査の入力経路を増やすため、単純さが失われる」としていました。**実際に A と B を検討した結果、どちらも採れないと判断しました。** 理由は §2 です。

## 2. A と B を採らなかった理由

### 案A(`types: [..., edited]` を加える)には安全上の問題があります

**13ジョブが毎回走る費用の問題だけではありません。**

費用を抑えるためにジョブ側へ `if:` を置いて `edited` のときは `pr-base-check` だけ走らせる、という形にすると、**集約ジョブが壊れます。**

```yaml
gate-g5:
  needs: [config, contract, test, ...]
  steps:
    - run: |
        if ${{ contains(needs.*.result, 'failure') || contains(needs.*.result, 'cancelled') }}; then
```

**`skipped` は `failure` でも `cancelled` でもありません。** 他のジョブを飛ばすと、集約は「失敗なし」と判定します。

**つまり、本文を編集しただけで `gate-g5` が緑になります。** テストも静的解析も走っていない状態で、必須ステータスチェックが通ります。**これは #95 が防ごうとしたものより重い穴です。**

`if:` を置かずに A を採る(=毎回13ジョブ)なら安全ですが、**`edited` は本文だけでなく題名の変更でも発火します。** `docs` 系の PR は推敲が多く、実行回数はそれなりに増えます。

### 案B(別ワークフローへ分ける)は集約の設計を壊します

**必須ステータスチェックは `gate-g5` ひとつです。** ワークフロー冒頭にその理由が書かれています。

> 個々の検査ジョブではなく、集約ジョブ1つを必須にすることで、検査を足しても保護設定を変えずに済みます

**別ワークフローの `pr-base-check` が緑になっても、`gate-g5` の赤は消えません。** GitHub はワークフローごとに最新の実行結果を持つためです。**`gate-g5` を通すには結局 `gate-g5` を再実行する必要があり、問題は解けません。**

**別ワークフローを必須チェックへ加えれば解けますが、それは「保護設定を変えずに済む」という設計を捨てることです。**

## 3. 直した内容

| ファイル | 変更 |
| --- | --- |
| `scripts/gate/pr-base-check.mjs` | `--pr` / `PR_NUMBER` があれば `gh pr view --json body,baseRefName` で取り直す。**本文の出所を必ず出力する** |
| `.github/workflows/gate-g5.yml` | `PR_NUMBER` と `GH_TOKEN` を渡す。`PR_BODY` は控えとして残す |
| `tests/gate/test_pr_base_check.py` | 検証4件を追加 |

**マージ先(`baseRefName`)も取り直します。** 本文と同じ機序で、ベースを張り替えてもイベントの値は古いままだからです。

### 落ちたときに手順を出します

```
  **本文を編集しただけでは CI は起動しません。** pull_request の既定の types に edited が
  含まれないためです(#119)。理由を書いたら、次のどちらかを実行してください。
    gh run rerun --failed <run-id>
    (または新しいコミットを積む)
  再実行では、本検査が GitHub API から「いまの本文」を読み直します
```

**#119 が報告した3つの操作のうち、2番目(`gh run rerun --failed`)が通るようになります。** 本変更前は、再実行しても同じイベントペイロードが再生されるため落ち続けました。

**費用は2ジョブです**(`pr-base-check` と集約の `gate-g5`)。13ジョブを毎回走らせる案A より小さく、案B のように保護設定を触りません。

### 残る手作業

**本文を編集しただけでは、まだ自動では起動しません。** 再実行の操作が1回要ります。

**「気づかない」ことが #119 の核心でした。** 検査自身が手順を出すことで、気づく契機を検査の中に置きます。

## 4. API を引けないときは落としません

**イベントの値へ落とし、落としたことを出力します。**

```
GitHub API から取り直せませんでした(...)。イベントの値を使います
本文の出所: イベントのペイロード
```

**API が引けないことを理由に検査を実施しない経路は作りません。** 出所が出力に残るため、「理由を書いたのに落ちる」が再び起きたときに切り分けられます。

## 5. `merged-reachability` に同じ機序はありません

**確認しました。** `merged-reachability.mjs` はイベントペイロードを読みません。

| 項目 | 実装 |
| --- | --- |
| 起動 | `push: [main]` / `schedule` / `workflow_dispatch`。**`pull_request` ではない** |
| データ | 実行時に `gh pr list --state merged --json ...` を引く |
| 判定 | `git merge-base --is-ancestor` で、その時点の `origin/main` と突き合わせる |

**どちらも実行時に取り直すため、古い値で判定する経路がありません。**

`--pr-json` はテストが `gh` に依存しないための入口で、CI では使いません。

## 6. 検証

```
$ node scripts/gate/pr-base-check.mjs --base main        → exit 0。本文の出所を出力
$ node scripts/gate/pr-base-check.mjs --base docs/x      → exit 1。再実行の手順を出力
$ pytest tests/gate                                      → 71 passed
$ ruff / spec-lint / double-encoding                     → すべて緑
```

追加した検証:

| # | 確かめたこと | 結果 |
| --- | --- | --- |
| 1 | **本文の出所を必ず出力する** | 出た |
| 2 | PR 番号が無ければイベントの値を使う | 通った |
| 3 | **API を引けないときはイベントの値へ落ちる**(検査を実施しない経路を作らない) | 通った |
| 4 | **失敗のときに再実行の手順を出す** | 出た |

## 7. 参照

- [#119](https://github.com/Takenori-Kusaka/Filetto/issues/119) — 本件の報告
- [#95](https://github.com/Takenori-Kusaka/Filetto/issues/95) / [PR #98](https://github.com/Takenori-Kusaka/Filetto/pull/98) — 検査の出所
- [PR #117](https://github.com/Takenori-Kusaka/Filetto/pull/117) — 事象が起きた PR

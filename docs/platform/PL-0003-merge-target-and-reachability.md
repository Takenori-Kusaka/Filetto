# PL-0003: マージ先が main でない PR を、発生させない・通さない・見逃さない

対象 Issue: [#95](https://github.com/Takenori-Kusaka/Filetto/issues/95)
作成: 2026-08-13 / レーン: Platform

## 1. 3層のうち、どこまで入れたか

| 層 | 依頼 | 状態 |
| --- | --- | --- |
| 1 | 発生させない — `delete_branch_on_merge` を `true` にする | **完了**(2026-08-13 に適用) |
| 2 | 通さない — ベースが `main` でない PR を検出する | **完了**(`pr-base-check`) |
| 3 | 見逃さない — マージ済み PR が `main` に到達したかを検査する | **完了**(`merged-reachability`) |
| — | stale ブランチの掃除 | **未実施。削除は不可逆のため PO の確認を待ちます**(§5) |

## 2. 層1: `delete_branch_on_merge`

```
$ gh api -X PATCH repos/Takenori-Kusaka/Filetto -F delete_branch_on_merge=true
true
```

**これで GitHub が子 PR のベースを `main` へ自動で張り替えます。** 張り替えは「ベースブランチが削除されたとき」に発火するため、`false` の間は一度も働きませんでした。

## 3. 層3: 到達の検査(`merged-reachability`)

### ブランチ先端では判定できません

**最初にブランチ先端で祖先判定を試み、64件中63件が「未到達」と出ました。**

**squash マージは新しいコミットを作るため、正常にマージされた PR でもブランチ先端は `main` の祖先になりません。** 判定に使えるのは **PR のマージコミット**です。

```
祖先である(削除しても失われない): 1 件
祖先でない(main に無い commit を持つ): 63 件   ← 先端で測った結果。使えない
```

### マージコミットで測った結果

**Issue #95 の調査と完全に一致しました。**

```
検査したマージ済み PR: 64 件
到達している: 61 件

マージ先が main でない PR: 3 件
  #87 base=docs/adr-decisions-0010
  #73 base=docs/d0-v1.4-scope-correction
  #6  base=docs/s0-001-graphify-spike

到達していない PR: 3 件
```

**PR #6 / #73 / #87 の3件。Issue の表と同じです。**

### 別経路で到達済みの扱い

**この3件は内容としては `main` へ到達しています**(#73 → PR #74、#87 → PR #94、#6 → 別経路)。**マージコミットは永久に祖先になりません。** 例外として書けなければ、検査は永久に赤のままになります。

`scripts/gate/pr-base-policy.json` の `resolved` へ、**PR 番号・到達させた経路・理由**を書きます。

```json
{ "pr": 87, "resolvedBy": "PR #94", "reason": "F-001〜F-003 の是正は PR #94 として main ベースで出し直し済み" }
```

**件数と理由を必ず出力します。黙って通しません。**

```
別経路で到達済みと確認した PR: 3 件
  #87 PR #94  F-001〜F-003 の是正は PR #94 として main ベースで出し直し済み
  ...
```

**`resolved` に書いた PR が後で到達した場合は失敗させます。** 到達済みのものを例外に残すと、以後の未到達を見落とすためです。

### 実行の形

`.github/workflows/merged-reachability.yml`。**G-5 には入れません。** PR 単位の検査ではなく、リポジトリ全体の状態の検査だからです。

| 契機 | 理由 |
| --- | --- |
| `main` への push | マージ直後に分かる。**#87 は当日中に見つかりました** |
| 毎日 06:00 JST | push が無い日も見る |
| 手動 | 調査のため |

**失敗したら `state:needs-platform` で Issue を起票します。** 定期実行の失敗は通知に埋もれるためです。

## 4. 層2: マージ先の検査(`pr-base-check`)

### 落とす設計にしました。ただし積み上げは禁じません

**PO は「警告 + 理由の記載を求める」で足りるとしています。** 装置を作る側として、**警告だけでは理由の記載を求めたことにならない**と判断しました。

| マージ先 | PR 本文 | 判定 |
| --- | --- | --- |
| `main` | — | **通る**。マージ先が `main` であることを出力する |
| `main` 以外 | `積み上げの理由:` を含む行がある | **通る**。理由を出力し、張り替えを促す |
| `main` 以外 | 記載が無い / 理由が空 | **落とす** |

**積み上げそのものは禁じていません。** 正当な場面があるという PO の判断に従っています。求めているのは、**作者が承知していることの記録**です。

**マージ先を特定できない場合も落とします。** 特定できないまま通すと、検査を実施していない状態を通過した記録として残ります。

目印(`積み上げの理由:`)と既定ブランチは `pr-base-policy.json` に持ちます。運用に依存する値を検査の定数にしません。

## 5. stale ブランチの掃除(PO の確認を待ちます)

**削除は不可逆です。実行していません。**

### 現状

```
ブランチ総数(main を除く): 63
```

| 区分 | 件数 | 削除 |
| --- | --- | --- |
| A. マージ済み PR のブランチ | **61** | **候補** |
| B. 未マージの open PR がある | 0 | しない |
| C. PR が閉じられたがマージされていない | **2** | **しない** |
| D. PR が1件も無い | 0 | しない |

C の2件は `docs/g2-record-rework`(PR #46)と `fix/session-definitions-deploy`(PR #35)です。**マージされていないため、内容が失われます。**

### 安全性をどう確かめたか

**「ブランチ先端が `main` の祖先か」では確かめられません**(§3)。squash マージのため、61件すべてが「祖先でない」と出ます。

**確かめられるのは PR 単位です。** `merged-reachability` が「61件が到達済み、3件は別経路で到達済み」と出しています。**A の61件は、内容が `main` またはその出し直し先へ到達しています。**

### 実行するなら

```bash
# 先に一覧を出す(削除しない)
gh pr list --repo Takenori-Kusaka/Filetto --state merged --limit 300 \
  --json number,headRefName --jq '.[]|.headRefName' | sort -u

# 確認後に削除する
gh api -X DELETE repos/Takenori-Kusaka/Filetto/git/refs/heads/<branch>
```

**PO の確認を待ちます。** 削除しなくても、`delete_branch_on_merge` により**今後のブランチは残りません。** 掃除は過去分だけの話です。

## 6. 検証

```
$ node scripts/gate/merged-reachability.mjs
  → 64 件を検査、到達 61 件、別経路で到達済み 3 件、未到達 0 件、判定不能 0 件 (exit 0)

$ node scripts/gate/pr-base-check.mjs --base main                → exit 0
$ node scripts/gate/pr-base-check.mjs --base docs/foo            → exit 1(理由の記載が無い)
$ PR_BODY='積み上げの理由: 親 PR #10 の ADR に依存するため' \
  node scripts/gate/pr-base-check.mjs --base docs/foo            → exit 0

$ pytest tests/gate   → 27 passed
$ ruff check .        → All checks passed!
```

否定側:

| # | 対象 | 壊し方 | 結果 |
| --- | --- | --- | --- |
| 1 | 到達 | 孤立コミットをマージコミットとして与える | 落ちた |
| 2 | 到達 | マージコミットが無い | 落ちた(判定不能) |
| 3 | 到達 | 手元に無いコミット | 落ちた(判定不能) |
| 4 | マージ先 | `main` 以外・理由の記載が無い | 落ちた |
| 5 | マージ先 | 目印だけで理由が空 | 落ちた |
| 6 | マージ先 | マージ先を特定できない | 落ちた |
| 7 | マージ先 | 方針ファイルが無い | 落ちた |

**1 は `git commit-tree` で孤立コミットを作っています。** 祖先判定を模擬に置き換えると、検査を検査したことになりません。

**gh を呼ぶ経路は pytest から外しました。** 認証の無い環境で黙って skip する検査になるためです。**本物の PR 一覧を使う実行は `merged-reachability.yml` が担います。**

## 7. 参照

- [#95](https://github.com/Takenori-Kusaka/Filetto/issues/95) — 本件の依頼
- [PR #87](https://github.com/Takenori-Kusaka/Filetto/pull/87) / [PR #94](https://github.com/Takenori-Kusaka/Filetto/pull/94) — 発端と出し直し
- `docs/platform/README.md` — 検査を足すときの原則

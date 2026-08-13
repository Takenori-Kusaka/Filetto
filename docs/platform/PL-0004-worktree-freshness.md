# PL-0004: 作業ツリーが古い定義で動いていることを、見えるようにする

対象 Issue: [#95](https://github.com/Takenori-Kusaka/Filetto/issues/95) 依頼4(4層目)
作成: 2026-08-13 / レーン: Platform

## 1. 何を作ったか

| ファイル | 役割 |
| --- | --- |
| `.claude/hooks/worktree-freshness.mjs` | セッション開始時に、作業ツリーと `origin/main` の差を出力する |
| `.claude/worktree-freshness.json` | 既定ブランチと監視対象。運用に依存する値を定数にしません |
| `.claude/settings.json` | `SessionStart` フックとして登録 |
| `tests/gate/test_worktree_freshness.py` | 検証8件。実際に起きた事象の再現を含む |

**止めません。見えるようにするだけです。** 作業中にブランチにいるのは正常であり、問題は「気づかないまま古い定義で動くこと」です。PO が案 A を推した理由と同じです。

## 2. 案 A を、指示ではなく装置にしました

PO の案 A は「各ロールの起動時に差を出力する」ですが、**留意点として「ロール定義に手順として置く形になる。装置ではなく指示になる」**と書かれていました。

**`SessionStart` フックに登録することで、装置になります。** ロール定義に手順を書く必要はなく、遵守にも依存しません。

| | 案 A(指示) | 本実装(装置) |
| --- | --- | --- |
| どこに書くか | 各 `SKILL.md` の冒頭 | `.claude/settings.json` の1箇所 |
| 実行の保証 | エージェントが読んで従えば | **セッション開始時に必ず走る** |
| ロールが増えたとき | 全ロールへ追記 | 不要 |

## 3. 何を見るか

| # | 見るもの | なぜ |
| --- | --- | --- |
| 1 | 上流が消えているか | `delete_branch_on_merge: true` により、マージ済みブランチの上流は消えます |
| 2 | `origin/main` からの遅れ | 何コミット取り残されているか |
| 3 | **挙動を決めるファイルの差** | **これが本体** |

**1 と 2 だけでは足りません。** 「遅れているが、挙動に関わる差は無い」場合と区別できないためです。

監視対象(`watchedPaths`):

```
.claude/settings.json  .claude/guard.json  .claude/skills  .claude/agents
.gemini/commands       CLAUDE.md           AGENTS.md       process.config.json
```

## 4. 二点比較でなければ拾えません

**最初に三点比較(`git diff base...HEAD`)で実装し、実際の事象を拾えませんでした。**

```
$ git diff --name-only origin/main...origin/docs/log-process-compass-217 -- <watched>
(なし)
```

**三点比較は共通の祖先からの差を見るため、`main` 側だけが進んだ変更が出てきません。** 本件で見たいのは、まさにそれです(`main` が進み、手元が取り残された)。

二点比較(`git diff base HEAD`)に直したところ、**実際に QM を止めた事象が再現しました。**

```
$ git diff --name-only origin/main origin/docs/log-process-compass-217 -- <watched>
.claude/agents/tech-advisor.md
.claude/guard.json
.claude/settings.json          ← QM の gh pr merge を遮断していたもの
.claude/skills/audit/SKILL.md
.claude/skills/dev/SKILL.md
.claude/skills/platform/SKILL.md
.claude/skills/po/SKILL.md
.claude/skills/qm/SKILL.md
.claude/skills/task-breakdown/SKILL.md
.gemini/commands/dev.toml
CLAUDE.md
```

**11件。** このブランチに留まったロールは、この11件すべてを古い内容で読んでいました。

## 5. 出力

`main` の最新にいるとき:

```
[作業ツリー] main の最新です。origin/main との差はありません
```

**差が無いときも出力します。** 無言で終わると、フックが動いたのか動いていないのかが分かりません。

古いブランチに留まっているとき:

```
[作業ツリー] いま feature/stale にいます(main ではありません)
  上流 origin/feature/stale は消えています。**マージ済みの可能性が高いです。**
  origin/main より 49 コミット遅れています
  **ロールの挙動を決めるファイルが origin/main と違います: 11 件**
    .claude/settings.json
    CLAUDE.md
    ...
  **.claude/settings.json はセッション開始時に読まれます。**
  ブランチを切り替えたら Claude Code を再起動してください
```

**再起動の案内を含めています。** PO の指摘のとおり、ブランチを切り替えただけでは `settings.json` は反映されません。

## 6. 検証

一時ディレクトリへ小さな git リポジトリを作って確かめます。**本物のリポジトリは書き換えません。**

| # | 確かめたこと | 結果 |
| --- | --- | --- |
| 1 | `main` の最新なら「差はありません」と出す | 通った |
| 2 | ブランチにいることを出す | 通った |
| 3 | **`main` が進み、ブランチに留まった状態で、差分11件相当を列挙する** | 通った |
| 4 | 監視対象でないファイル(`README.md`)の差は列挙しない | 通った |
| 5 | `main` 自体が遅れていれば `git pull` を促す | 通った |
| 6 | **git の外でも落ちない** | 通った |
| 7 | 設定が既定ブランチと監視対象を持つ | 通った |
| 8 | **`SessionStart` フックとして登録されている** | 通った |

**6 は、フックが例外で落ちるとセッション開始そのものが壊れるためです。**
**8 は、置いただけで走らないフックは装置ではないためです**(`docs/platform/README.md` 検査を足すときの原則5)。

```
$ pytest tests/gate  → 21 passed
$ ruff check .       → All checks passed!
```

## 7. 残っていること

**このフックは Claude Code のセッション開始時にだけ走ります。** Gemini CLI には同等の仕組みが要ります([#91](https://github.com/Takenori-Kusaka/Filetto/issues/91) と同じ性質の論点です)。**本 PR の範囲外とし、記録に留めます。**

## 8. 参照

- [#95](https://github.com/Takenori-Kusaka/Filetto/issues/95) — 本件の依頼(4層目)
- [PL-0003](PL-0003-merge-target-and-reachability.md) — 1〜3層目

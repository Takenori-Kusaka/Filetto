# Platform レーンの記録と、強制層の変更手順

Platform は検査・リント・CI/CD の装置を作り、維持します。**判定は行いません。**

## 記録

| 番号 | 内容 |
| --- | --- |
| [PL-0001](PL-0001-ip-clearance-pep639.md) | `ip-clearance` の PEP 639 対応。SPDX 式の評価を自前へ移す |
| [PL-0002](PL-0002-session-definition-drift.md) | ロール定義の正本と各ランタイム向け生成物の乖離検出 |

## 強制層に触る変更をどう進めるか

**2026-08-13 時点で、エージェントから書けないファイルは1件もありません。強制層は動いていません。**

| 層 | 状態 |
| --- | --- |
| `permissions.deny` | **空** |
| **`PreToolUse` hook(`guard-write.mjs`)** | **`.claude/settings.json` に登録されていない。呼ばれない** |

**これは意図した状態です。** 序盤フェーズは `.claude/` をプロダクトへ合わせて最適化している期間であり、その期間中に遮断をかけたまま運用しない、という事業決裁者の判断によります([ADR-0015](../../context/decisions/0015-enforcement-scope-during-optimization.md))。

**そのため、次の5点は機械では止まりません。指示の遵守だけで保たれています。**

| # | 止まらないもの | 保つ根拠 |
| --- | --- | --- |
| 1 | `.claude/settings.json` / `process.config.json` の書き換え | `CLAUDE.md` 禁止事項6 |
| 2 | **`gh pr review` / `gh pr merge`**(セルフ・アプルーブ) | `CLAUDE.md`「AI レビューは判定に使わない。承認もしない」 |
| **3** | **自己修正ループ中のテストの改変** | **`CLAUDE.md` 禁止事項3** |
| 4 | 秘密情報の読み取り・force push | ロール定義 |
| 5 | `PROCESS-PROFILE.md` / `CODEOWNERS` / `.claude/guard.json` の書き換え | 本ページの手順 |

**3 が最も重いものです。** これまで機械で止めていた唯一の「実装の質に直接効く」遮断であり、**テストが実装の誤りを検出しなくなることに直結します。**

**hook 本体(`.claude/hooks/guard-write.mjs`)と `.claude/guard.json` は残しています。** 見直しのときに書き直すのは無駄なため、**呼び出しを外しただけです。**

**遮断範囲の再設計は [#75](https://github.com/Takenori-Kusaka/Filetto/issues/75) で行います。`status:on-hold` です。**

### 2026-08-13 に遮断を縮めた(Owner の操作)

本 Issue #60 の作業中に、遮断が実務を止めていることが分かりました。**`scripts/gate/**` が遮断されているために、Platform レーンが自分の成果物である検査スクリプトを書けませんでした。** 人が `cp` を1行打つ作業が発生し、その1行が判断の質を上げることはありません。

変更は2ファイルにわたります。**性質が異なるため、分けて記録します。**

#### `guard.json` の `protectedPatterns` を縮めた

| 対象 | 外した理由 |
| --- | --- |
| `scripts/gate/**` / `adapters/**` | **Platform レーンの成果物そのもの。** 変更は PR の差分に出て、G-6 独立レビューで人が見ます |
| `.github/workflows/**` / `.github/rulesets/**` | 同上。CI 定義の変更は差分に出ます |
| `.claude/hooks/**` | 同上 |
| `scripts/vendor/**` | 同上 |

**当時「残した」と書いたのは** `.claude/settings.json` / `.claude/guard.json`(遮断の定義そのもの)、`process.config.json` / `PROCESS-PROFILE.md`(有効なゲートの正本)、`CODEOWNERS` **です。**

**ここは「差分に出ないものだけ遮断する」という線引きでした。**

> **訂正(2026-08-13)**
>
> **上の記述は実態と食い違っていました。** 2026-08-13 の実測で、`.claude/settings.json` と `process.config.json` が**遮断を通過する**ことが分かりました([#70](https://github.com/Takenori-Kusaka/Filetto/issues/70))。
>
> ```
> .claude/settings.json  exit=0  通過
> process.config.json    exit=0  通過
> .claude/guard.json     exit=2  遮断
> ```
>
> **事業決裁者は「何も戻さなくていい」と判断しました。** 経緯と受容したリスクは [ADR-0015](../../context/decisions/0015-enforcement-scope-during-optimization.md) にあります。**PR #65 のコミットメッセージも同じ食い違いを含みますが、書き換えられないため本節で訂正を残します。**

#### `settings.json` の `permissions.deny` を空にした

**こちらは上の線引きとは別です。** `deny` には強制層以外のものも入っており、それらもあわせて外れました。

| 外れたもの | 何を止めていたか |
| --- | --- |
| `Read(./.env)` `**/*.pem` `**/*.key` `**/id_rsa*` `**/.aws/**` `**/.ssh/**` | 秘密情報の読み取り |
| `Bash(git push --force:*)` / `-f` | 履歴の破壊 |
| **`Bash(gh pr review:*)` / `Bash(gh pr merge:*)`** | **AI による承認とマージ** |
| `Bash(gh api repos/*/rulesets:*)` | ブランチ保護の書き換え |
| `Edit(./scripts/gate/**)` ほか強制層の各種 | 上の `guard.json` と同じ範囲 |

**`gh pr review` / `gh pr merge` の遮断が外れている点は、記録として残します。** `CLAUDE.md` は「AI レビューは監査の入力であり、判定には使わない。承認もしない」と定めており、G-6 独立レビューと G-7 出荷判定の前提でもあります。**外れた後は、この前提を指示だけで保っています**(**2026-08-13 に hook の登録も外したため、禁止事項3 も同じ状態です**)。

**Owner の判断です。** 戻す場合は `deny` へ上表の項目を書き戻します。

> **判断(2026-08-13)**: **戻しません。** 序盤フェーズの間は `deny` を空のまま運用します([ADR-0015](../../context/decisions/0015-enforcement-scope-during-optimization.md) 決定1)。**見直しは G-4 通過後、[#75](https://github.com/Takenori-Kusaka/Filetto/issues/75) で行います。**

### 残る手順

**遮断されている `.claude/guard.json` / `PROCESS-PROFILE.md` / `CODEOWNERS` に触る場合だけ**、次の順序で進めます。**`.claude/settings.json` と `process.config.json` は遮断されていませんが、合否条件の正本であるため同じ手順を踏んでください。**

1. **Platform が変更内容を `docs/platform/proposed/` に置く。** 配置先と同じ名前にする
2. **Platform が検証結果を PL-NNNN として記録する。** 実測の出力を貼る。「通るはず」は書かない
3. **Platform がテストを `tests/` へ置く。** CI から必ず走る経路まで用意する
4. **人が適用する。** 適用コマンドは PR 本文へ、そのまま貼れる形で載せる
5. **適用後、`docs/platform/proposed/` から消す。** 正本が2箇所にある状態を残さない

## 残っている確認待ち

`.claude/settings.json` の `ask` に次が残っています。**いずれも取り消せる操作で、確認待ちにする必要はありません。**

```
Bash(git push:*)   Bash(gh pr create:*)   Bash(curl:*)   Bash(wget:*)
```

`ask` は permission mode が bypass でも確認待ちになります。**「bypass にしているのに止まる」の原因はここです。** 外す場合は `ask` を公開系(`Bash(npm publish:*)` / `Bash(twine upload:*)`)だけに絞ります。判断者は **Owner** です(エージェントは自分を縛る設定を変えません)。

2026-08-13 時点では未対応のまま残しています。

## 検査を足すときの原則

| # | 原則 |
| --- | --- |
| 1 | **検査が通ることと、正しいことは別である** |
| 2 | **黙って通る検査を作らない。** 対象が0件のときは、0件であることを出力する |
| 3 | 運用に依存する値を定数にしない(`context/standards/extensibility.md`) |
| 4 | 検査の追加・変更は、機能変更と混ぜない |
| 5 | **テストを置いたら、CI から走ることまで確かめる。** 置いただけのテストは検査ではない |

# ADR-0015: 最適化期間中の強制層の範囲を定め、記録を実態へ合わせる

## ステータス

採用(2026-08-13)

## コンテキスト

2026-08-13、[#70](https://github.com/Takenori-Kusaka/Filetto/issues/70) で強制層の実測を報告した。**記録が「残した」と書いている対象の一部が、実際には遮断されていなかった。**

### 実測

```
$ node .claude/hooks/guard-write.mjs  (Edit の入力を与えて終了コードを取得)

.claude/settings.json            exit=0  通過
process.config.json              exit=0  通過
.claude/guard.json               exit=2  遮断
scripts/gate/spec-lint.mjs       exit=0  通過
```

```
$ 実際の protectedPatterns          $ 実際の permissions.deny
  .claude/guard.json                  []
  PROCESS-PROFILE.md
  CODEOWNERS
  .github/CODEOWNERS
```

### 記録との食い違い

**3か所が「残した」と書いていた対象のうち、次が外れていた。**

| 分類 | 対象 | 記録 | 実態 |
| --- | --- | --- | --- |
| A 自己言及 | `.claude/settings.json` | 残した | **外れている** |
| A 自己言及 | `.claude/hooks/**` | 差分に出るので外す | 外れている(記録どおり) |
| B 合否条件の正本 | `process.config.json` | 残した | **外れている** |
| — | `permissions.deny` 全件 | Owner の判断 | **空** |

**`.claude/settings.json` が書ければ、他の遮断はすべて無効にできる。** hooks は実行中セッションへ即時リロードされるため、hook 本体を書き換えれば `guard.json` を読まなくできる。

**`gh pr review` / `gh pr merge` の遮断も消えている。** 標準 [3.5.1](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) が物理分割の理由として第一に挙げた「作成者 ≠ 承認者ルールの機械的強制」が、機械では担保されていない。

### 事業決裁者の判断

不可逆4操作(ガードの削除)に当たるため `state:needs-owner` で判断を仰いだ。回答は次のとおり。

> **何も戻さなくていいです。**(2026-08-13)

> **重複しているゴミファイルは削除していいですし、guard はもっとプロダクトに特化した形で行うべきです。この序盤フェーズでは `.claude` をプロダクトに合わせて最適化しているフェーズであり、この期間中に制限をかけたまま運用するのは不適切です**(2026-08-13)

## 決定

### 1. ファイルの書き込み遮断は現状のまま。戻さない

**遮断されるのは次の4パターンのみである。**

```
.claude/guard.json
PROCESS-PROFILE.md
CODEOWNERS
.github/CODEOWNERS
```

**`.claude/settings.json` / `process.config.json` / `.claude/hooks/**` / `scripts/gate/**` は書ける状態のままとする。**

### 1-2. ただし、承認とマージの遮断は戻す

**`permissions.deny` へ次の3件を書き戻す。**

```
Bash(gh pr review:*)
Bash(gh pr merge:*)
Bash(gh api repos/*/rulesets:*)
```

**決定1 と分ける理由は、緩和の根拠が及ばないためである。**

**緩和の根拠は「`.claude/` をプロダクトへ最適化している期間だから」であった。** ファイルの書き込み遮断は、その作業を直接止める。**`scripts/gate/**` の遮断で人が `cp` を1行打つ作業が発生した前例がある。**

**承認とマージの遮断は、その作業を一切止めない。** `.claude/` の最適化に `gh pr merge` は要らない。**緩和の便益がゼロであり、失われるものだけが残る。**

**失われるのは、標準 [3.5.1](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) が物理分割の第一の理由に挙げたものである。**

> 単一の作業領域で AI エージェントを自走させた場合、AI が同一コンテキスト内でコードを書き(R)、そのまま自分の PR を自分で承認(A)してマージする「セルフ・アプルーブ」を防ぐことは極めて困難である

### 1-3. `git push --force` は戻さない

**`Bash(git push --force:*)` と `Bash(git push -f:*)` は書き戻さない。**

**理由は、`--force-with-lease` を巻き込むためである。** `Bash(git push --force:*)` は前方一致であり、**`git push --force-with-lease` も遮断される。**

**本案件は rebase したブランチの再 push を実務で使っている**([PR #87](https://github.com/Takenori-Kusaka/Filetto/pull/87) で `main` へ rebase した)。`--force-with-lease` は他者の push を上書きしない安全な形であり、**これを止めると rebase の運用が成立しない。**

**`--force` だけを遮断して `--force-with-lease` を通す表現が、いまの `permissions` の書式で作れるかを確認できていない。** **確認できるまで、履歴の破壊は指示の遵守で保つ。**

**この判断は暫定である。** [#75](https://github.com/Takenori-Kusaka/Filetto/issues/75) の再設計で扱う。

### 2. 記録を実態へ合わせる

**3か所の記述を、実測した状態へ書き換える。**

| 場所 | 何を直すか |
| --- | --- |
| `docs/platform/README.md` | 「書けません」の一覧から `.claude/settings.json` と `process.config.json` を外す。**遮断が外れている期間であることを明記する** |
| `context/projects/P-001.md` 運用上の注意3 | 保護対象の表を実測へ合わせる |
| PR #65 のコミットメッセージ | **書き換えられない。** 本 ADR で訂正を残す |

**記録が実態より強く書かれている状態を残さない。** 「守られている」と読める記述は、守られていないときに最も害が大きい。

### 3. 失われた統制は、指示の遵守で保つ

**機械で止まらなくなった次の3点は、`CLAUDE.md` とロール定義の遵守だけで保つ。**

| # | 対象 | 保つ根拠 |
| --- | --- | --- |
| 1 | `.claude/settings.json` / `process.config.json` の書き換え | `CLAUDE.md` 禁止事項6 |
| 2 | 秘密情報の読み取り・force push | ロール定義 |

**これは弱い担保である。** 弱いことを承知のうえで受容する。

**`gh pr review` / `gh pr merge` は当初この表にあったが、決定1-2 で機械の遮断へ戻した。** 指示の遵守で保つ対象から外れている。

### 4. 見直しの時期を決める

**`.claude/` の最適化が完了した時点で、遮断範囲を再設計する。**

**最適化の完了とは、次の2つを満たすことをいう。**

| # | 条件 |
| --- | --- |
| 1 | ロール定義(`.claude/skills/**`)と各ランタイム向け生成物の乖離検出が動いている([#43](https://github.com/Takenori-Kusaka/Filetto/issues/43)) |
| 2 | **G-4 を通過し、実装が始まっている。** 序盤フェーズの終わり |

**再設計は [#75](https://github.com/Takenori-Kusaka/Filetto/issues/75) と [#91](https://github.com/Takenori-Kusaka/Filetto/issues/91) で行う。両者は `status:on-hold` である。**

### 5. 再設計では「プロダクトに特化した形」を採る

**事業決裁者の指示による。** テンプレート由来の遮断一覧をそのまま戻すのではなく、本案件で実際に守りたいものから設計する。

**設計の起点にする問い**

| # | 問い |
| --- | --- |
| 1 | **本案件で、機械が止めなければ止まらないものは何か** |
| 2 | 差分に出るものは、どのゲートの誰が見るか |
| 3 | 遮断が実務を止めた実績があるものは何か(`scripts/gate/**` の前例) |

## 採らなかった選択肢

### 案A: A(`.claude/settings.json` / `hooks/**`)と B(`process.config.json`)を戻す

**pit-in-template#19 の論旨が「既定で残す」としていた対象である。** 標準 E.7 は「差分からの事後検出だけでは層が働かない」と明記しており、`agent-trace-control` は検査の除外設定を G-6 ではなく **G-5 で止めよ**と定めている。**本案件の G-6 は未達であり、「G-6 で見られる」という前提が成立しない。**

**採らなかった理由**: **いま `.claude/` を書き換えている最中である。** 遮断を戻すと、`.claude/settings.json` を触るたびに人の手作業が挟まる。**その手作業が判断の質を上げないことは、`scripts/gate/**` の前例で実測済みである**(人が `cp` を1行打つだけだった)。

**この判断は期間限定である。** 決定4 の条件を満たしたら案A を再検討する。

### 案B: `gh pr review` / `gh pr merge` を戻さない

**当初、本 ADR は案B を「採らなかった選択肢」として退けていた。** 理由は「物理分割が既に効いており、`deny` は三重目の担保であるため、いま戻す優先度は高くない」であった。

**この判断を撤回する。決定1-2 として採用した。**

**撤回の理由は、緩和の便益がゼロだと気づいたことである。**

**当初の判断は「戻す便益」と「戻さない便益」を比べていなかった。** 「三重目だから優先度が低い」は戻さない理由になるが、**戻すことの費用がゼロなら、優先度の高低は関係がない。**

**`.claude/` の最適化に `gh pr merge` は要らない。** 遮断しても作業は1つも止まらない。**費用ゼロ・便益ありのものを、優先度を理由に見送っていた。**

**きっかけは [pit-in-template#20](https://github.com/Takenori-Kusaka/pit-in-template/issues/20) の調査である。** `/process-init` が `permissions.deny` を全置換し、**安全重要度によらず `gh pr merge` / `gh pr review` の遮断を消す**ことが分かった。**テンプレートを使う案件は既定でこの穴を持つ。**

**本案件の `deny` が空になった経緯は [PR #65](https://github.com/Takenori-Kusaka/Filetto/pull/65) の手動操作であり、この欠陥とは別である。** しかし**「気づかないまま外れている」という同じ結果に至っている。**

### 案C: 遮断を戻したうえで、`.claude/**` を触るとき限定の例外手順を作る

**採らなかった理由**: **例外手順は、それ自体が守られたか確かめる手段を要する。** 手順を作るコストと、手順が守られたかを見るコストが、遮断が防ぐものより大きい。**序盤フェーズの短い期間のために作る装置ではない。**

### 案D: 記録だけ直して ADR を残さない

**採らなかった理由**: **「戻さない」は判断である。** 標準 3.8.1 は統制の弱化を記録の対象としている。**後から「なぜ遮断が外れているのか」を追う経路が要る。** 記録の修正だけでは、外れている状態が既定に見える。

## 帰結

### 受け入れるもの

| # | リスク |
| --- | --- |
| 1 | **エージェントが `.claude/settings.json` を書き換え、他の遮断を無効にできる** |
| 2 | エージェントが `process.config.json` のカバレッジ閾値を書き換えられる |
| ~~3~~ | ~~エージェントが自分の PR を承認してマージできる~~ **→ 決定1-2 で遮断へ戻した** |
| 4 | 秘密情報の読み取り・force push が機械で止まらない |

**1 が最も重い。これを書ければ、決定1-2 で戻した遮断も無効にできる。** 「指示の遵守」だけで保たれている。

**4 のうち force push については、決定1-3 に理由を書いた。**

### 検出の経路

**遮断が効かない代わりに、差分に出る。**

| 対象 | 差分に出るか | 見る場所 |
| --- | --- | --- |
| `.claude/settings.json` | **出る** | G-6 独立レビュー(**未達**) |
| `process.config.json` | **出る** | 同上 |
| `gh pr merge` の実行 | **出ない** | **決定1-2 で機械が遮断する。差分に出ないものを指示だけで保つ形をやめた** |

**G-6 が未達である間、1 と 2 を見る工程が無い。** これが本 ADR で受容する範囲の中で最も弱い箇所である。

**決定1-2 は、この表の3行目を消すための変更である。「差分に出ない」かつ「見る工程が無い」ものを、指示の遵守だけで保つ構成にしない。**

### 範囲設計と独立に見つかった欠陥

**遮断範囲とは別に、hook 自体の欠陥が4件ある**([#75](https://github.com/Takenori-Kusaka/Filetto/issues/75))。

| # | 欠陥 |
| --- | --- |
| 1 | **Windows で `.claude/GUARD.json` が同一ファイルでありながら遮断を通過する**(全パターン迂回可能) |
| 2 | オブジェクト形式の設定は、古い hook と組み合わさると例外もログもなく全遮断が消える |
| 3 | **hook のテストが0件** |
| 4 | `denied.log` が git 管理外で、全ワークツリー実質0件 |

**本 ADR は範囲の決定のみを扱う。** 欠陥の修復は #75 で扱い、`status:on-hold` である。**遮断が効いていない期間に hook を直しても、直ったことを確かめられない。**

## 参照

- [#70](https://github.com/Takenori-Kusaka/Filetto/issues/70) 実測の報告と事業決裁者の判断
- [#75](https://github.com/Takenori-Kusaka/Filetto/issues/75) hook の欠陥4件(保留)
- [#91](https://github.com/Takenori-Kusaka/Filetto/issues/91) Gemini CLI での遮断(保留)
- [pit-in-template#19](https://github.com/Takenori-Kusaka/pit-in-template/issues/19) 遮断範囲の3分類 A/B/C
- [ADR-0009](0009-claude-code-permissions-no-ask.md) `permissions` を allow/deny の二値にする
- 標準 [第3章 3.5.1](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) 物理分割
- 標準 [附属書E E.7](https://takenori-kusaka.github.io/process-compass/phase4-process-design/developer-guide/) 強制層

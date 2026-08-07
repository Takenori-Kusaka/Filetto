# ブランチ保護

`process.config.json` の `ruleset` が、適用するファイルを指します。

| ファイル | 適用する場面 | 承認数 | 署名 |
| --- | --- | --- | --- |
| `team.json` | 3名以上。標準品質 | 1 | 任意 |
| `regulated.json` | 規制業、または安全重要度 CL2 以上 | 2 | 必須 |
| (なし) | 1〜2名 | — | — |

1〜2名の構成ではルールセットを置きません。作成者の自己承認を止める設定は、承認者が別に存在して初めて意味を持つためです。この場合、独立レビュー(G-6)は**未達**として `PROCESS-PROFILE.md` に残ります。

## 適用のしかた

```bash
gh api repos/{owner}/{repo}/rulesets --input .github/rulesets/team.json
```

適用済みのルールセットを確認します。

```bash
gh api repos/{owner}/{repo}/rulesets --jq '.[] | "\(.id) \(.name) \(.enforcement)"'
```

## なぜここに置くか

指示ファイルへ「作成者は自分の PR を承認しない」と書いても、遵守は保証されません。**強制層(ホスティングの設定)に置いた項目だけが、遮断できたものとして数えられます**。

`require_last_push_approval: true` が要点です。これがないと、承認を得たあとに自分で push して内容を変えられます。

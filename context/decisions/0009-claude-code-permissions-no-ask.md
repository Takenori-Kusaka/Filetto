# ADR-0009: Claude Code の権限設定から `ask` を廃し、allow/deny の二値で運用する

## ステータス

採用(2026-08-13)

## コンテキスト

`.claude/settings.json` の `permissions` には、テンプレート由来の `ask` が5件あった。

```
"ask": [
  "Bash(git push:*)",
  "Bash(gh pr create:*)",
  "Bash(npm publish:*)",
  "Bash(curl:*)",
  "Bash(wget:*)"
]
```

`ask` は Claude Code の権限判定で `deny` の次に強く、**`bypassPermissions` モードでも確認ダイアログを出す**。本リポジトリの開発サイクル(`/dev` → `/qm` の Label Mailbox 連携)は `git push` と `gh pr create` を毎サイクル必ず通るため、自走させても毎回そこで停止していた。

停止の実害は「待たされること」だけではない。**確認が高頻度で発生すると、内容を読まずに承認する習慣がつく。** 確認の回数が増えるほど1回あたりの注意は薄まり、確認そのものが形骸化する。本リポジトリは `state:*` ラベルによる非同期な引き渡しと、G-6(独立レビュー)を人が担うことで安全性を確保しており、**個々のコマンド実行時点での対話的確認は、その安全性の構成要素になっていない。**

一方で、本当に止めるべき操作は `ask` ではなく `deny` に置くべきである。`ask` は「人が承認すれば通る」経路であり、自走するエージェントに対しては「承認を求めれば通る」経路と等しい。

## 決定

### 1. `permissions.ask` を廃止する。allow と deny の二値で運用する

「聞けば通る」中間状態を持たない。ある操作は、**自走してよいか(allow)、絶対に通してはならないか(deny)** のどちらかに分類する。

### 2. `ask` にあった5件はすべて `allow` へ移す

| コマンド | 移し先 | 理由 |
| --- | --- | --- |
| `git push` | allow | 毎サイクル通る。`--force` / `-f` は deny に据え置き。`main` の保護はブランチ保護規則(サーバ側)が担う |
| `gh pr create` | allow | 毎サイクル通る。PR の作成は可逆であり、マージ(`gh pr merge`)と承認(`gh pr review`)は deny のまま |
| `npm publish` | allow | 本プロジェクトは Python スタックであり、実行経路が存在しない。禁止する意味も、確認する意味もない |
| `curl` / `wget` | allow | 調査・API 参照で日常的に使う。ネットワーク境界を Claude Code の権限設定で守る設計にはしない |

### 3. Label Mailbox 運用で必ず通るコマンドを allow に追加する

`gh pr edit` / `gh pr comment` / `gh issue edit` / `gh issue comment`(= `state:*` ラベルの付け外し)、`gh pr checks` / `gh run list` / `gh run view`(= CI 結果の確認)、`gh api`、`git fetch` / `git pull` / `git checkout` / `git show` を追加する。

**ラベルの付け外しが確認待ちで止まると、CLAUDE.md の禁止事項7・8(ラベルを貼らない/剥がし忘れる)を運用が構造的に誘発する。**

### 4. 強制層の保護は変更しない

`.claude/settings.json` `.claude/guard.json` `.claude/hooks/**` `.github/workflows/**` `.github/rulesets/**` `process.config.json` `adapters/**` `scripts/gate/**` は、`deny` と `guard-write.mjs` の二重で引き続きエージェントの編集対象外とする。

**この ADR の変更それ自体も、人の手で適用した。** エージェントが自分を縛る設定を書き換えられる構成では、遮断が成立しない(`guard.json` の `protectedReason`)。権限設定の更新に人の一手が要ることは不足ではなく、設計上の要件である。

## 検討した選択肢

| 案 | 採らなかった理由 |
| --- | --- |
| `ask` を残したまま `bypassPermissions` を使う | Claude Code の権限判定では `ask` が `bypassPermissions` に優先する。問題が解消しない |
| `ask` の項目を減らす(`git push` と `gh pr create` だけ allow へ) | 残した項目が「なぜこれだけ確認するのか」を説明できない。`npm publish` は実行経路がなく、`curl` / `wget` は境界防御になっていない。基準のない確認は形骸化する |
| `ask` を `deny` へ落とす | `git push` と `gh pr create` を禁止すると開発サイクルが成立しない。`npm publish` のみ deny も検討したが、Python スタックで実行経路がなく、deny の一覧を実態のない項目で膨らませる意味がない |
| `.claude/settings.local.json`(個人設定)側で上書きする | 権限判定は `deny` > `ask` > `allow` の順で、ファイルの層より規則の種別が優先される。local 側の `allow` は project 側の `ask` を打ち消せない。技術的に不可能 |
| `settings.json` を保護対象から外し、エージェントが自分で権限を編集できるようにする | `settings.json` には `hooks` 定義も含まれる。編集できるようにすると、エージェントが `guard-write.mjs` の呼び出しごと削除でき、強制層に穴が開く。**保護の粒度がファイル単位である以上、権限だけを開けることができない** |
| `ask` を廃止せず、`bypassPermissions` を使わない運用へ戻す | 1〜2名体制で AI に実行(R)を担わせる前提と両立しない |

## 可逆性

| 項目 | 内容 |
| --- | --- |
| 後から変えられるか | **変えられる**(設定ファイル1つ、数行) |
| 変えるとしたら必要なこと | 人が `.claude/settings.json` を編集し、PR を出す。エージェント経由の経路はない(決定4) |
| いつまでなら安く変えられるか | いつでも |

## 影響

**得られるもの:**

- `bypassPermissions` モードで開発サイクルが最後まで自走する
- 確認の形骸化がなくなる。deny に載っているものは、承認では通らない
- 「止める判断」が deny の一覧に集約され、レビュー可能な一箇所になる

**トレードオフ:**

- **`curl` / `wget` / `gh api` が無確認で実行される。** 外部への送信を Claude Code の権限設定で止める経路がなくなる。この境界は、ネットワーク側および「認証・認可・個人データ・外部との契約に関わる変更は AI が担わない」という CLAUDE.md の委譲境界で担保する
- **`git push` が無確認になる。** `main` への直接 push は GitHub のブランチ保護規則(サーバ側)が拒否する。クライアント側の設定で守る構成には戻さない

**解決しないこと:**

- **`.claude/settings.json` の更新には引き続き人の一手が要る。** これは決定4のとおり意図された制約であり、解消の対象ではない。エージェントは変更内容とパッチを用意し、適用は人が行う

## 関連

- `CLAUDE.md`「ロール間非同期メッセージング(Label Mailbox 連携)」「行ってはならない作業」禁止事項7・8
- `.claude/guard.json` の `protectedPatterns` / `protectedReason`
- `.claude/settings.json`(本 ADR の適用対象)

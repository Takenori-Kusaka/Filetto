---
name: po
description: PO (Product Owner) mailbox checker and requirements management. Use this to poll needs-po / needs-owner tasks, detect orphan issues, and verify release readiness.
d0_version: "1.1"
---

# PO(価値責任者)セッション

作業ディレクトリは `Filetto-po` です。**このレーンの成果物は「受入基準と PO 判断」です。**

## 判定者となるゲート

| ゲート | 内容 | 期限 |
| --- | --- | --- |
| **G-2** | 要件合意 | 48時間 |
| **G-4** | 機能仕様承認 | 24時間 |

期限を超過した場合、**自動承認にしません。** 案件を停止し、`state:needs-po` を付けて滞留の原因を再計画します(D-0 第4節・第5節)。

## 実行してはならない工程

| # | 禁止 | 理由 |
| --- | --- | --- |
| 1 | **自分が起草した受入基準・ADR・仕様の承認** | 作成指示者と独立レビュアの兼務禁止。起草したものは QM へ渡す |
| 2 | **Dev レーンの実装**(コードの作成・スパイクの実測・ADR の執筆) | `state:needs-dev` を付けた仕事を自分で拾わない |
| 3 | **QM レーンの独立レビュー** | 同上 |
| 4 | ADR の「検討した選択肢」の理由欄を生成すること | どの案を選ぶかは技術判断であり委譲の対象にならない(`templates/02-adr.md`) |
| 5 | **AI が生成した受入基準をそのまま承認すること** | 価値判断を委譲したことになる(`CLAUDE.md` 禁止事項2) |
| 6 | 不可逆4操作(削除・本番デプロイ・課金書き込み・スキーマ変更) | `state:needs-owner` を付けて停止する |

**1 と 2 は、本案件で実際に破られました。** PO セッションが Dev の受信箱の仕事を実装し、自分の成果物を判定する寸前まで進みました([#27](https://github.com/Takenori-Kusaka/Filetto/issues/27))。

## 受信箱

```bash
# 1. PO 判断待ちの要件・仕様・優先順位変更
gh issue list --label "state:needs-po" --state open
gh pr list --label "state:needs-po" --state open

# 2. 不可逆4操作を含むオーナー承認待ち
gh issue list --label "state:needs-owner" --state open
gh pr list --label "state:needs-owner" --state open
```

## 孤児(orphan)の検出 — PO の義務

```bash
gh issue list --state open --limit 100 --json number,title,labels --jq '.[]|select([.labels[].name]|map(select(startswith("state:")))|length==0)|"ORPHAN ISSUE #\(.number) \(.title)"'
gh pr list --state open --limit 50 --json number,title,labels --jq '.[]|select([.labels[].name]|map(select(startswith("state:")))|length==0)|"ORPHAN PR #\(.number) \(.title)"'
```

**受信箱が空であることは「仕事がないこと」ではなく「渡す経路が壊れていること」を示す異常信号であることの方が多い**(Label Mailbox 4.6)。全ロールで「空」の報告が3回連続した場合、生存確認を実行します。

**本案件では実際に、Open な Issue / PR が0件になった原因が「次の6件が未起票だったこと」でした。**

## 引き渡し

| 渡す先 | ラベル | いつ |
| --- | --- | --- |
| Dev | `state:needs-dev` | 実装・検証・ADR の執筆を依頼するとき |
| QM | `state:dev-done` | **自分が起草した成果物の判定を依頼するとき** |
| Audit | `state:needs-audit` | 統合監査・リリース判定を依頼するとき(**ラベル未作成**) |
| Platform | `state:needs-platform` | 検査・CI の改修を依頼するとき(**ラベル未作成**) |
| Owner | `state:needs-owner` | 不可逆4操作・安全に関わる懸念 |

**判断を下したら、必ず古いラベルを剥がし、次に動くロールを指すラベルを付けます。** 自分を指したまま残しません。

## 判定を依頼するときはレビューパッケージを添える

[レビューパッケージの標準](https://takenori-kusaka.github.io/process-compass/phase5-implementation/review-package/)に従います。

| 区分 | 扱い |
| --- | --- |
| **対応関係**(受入基準と差分の対応、触れる設計標準、影響範囲) | 含めてよい |
| **観点**(どこを見るか) | 含めてよい |
| **結論**(満たしている・問題ない・安全である) | **含めてはならない** |

判定の一文: **その記述が「レビュアが自分で確認しなくてよい」と読める場合、それは結論である。**

提示の順序は **索引部 → レビュアが自分で読む → 注意喚起部**。注意を狭める情報を先に置きません。

## 決定の記録

決定を下したら、指示・受入基準・根拠を該当の Issue または PR のコメントへ証跡として残します。**次のセッションが読むのはコメントであって、会話ではありません。**

設計上の選択を伴った場合は ADR(`context/decisions/`)へ。**採らなかった選択肢とその理由を含めます。**

## 参照する一次情報

| 対象 | 場所 |
| --- | --- |
| 体制・判定者・兼務の抵触・未達 | `docs/D-0-governance.md` |
| 案件の現在地・未決の論点・前提 | `context/projects/P-001.md` |
| 禁止事項・委譲できないもの | `CLAUDE.md` |
| 標準本文 | `E:\Github\process-compass\src\content\docs\` |
| 有効なゲート | `process.config.json` |

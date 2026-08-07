# 成果物テンプレート

ピットイン方式の成果物11種です。使うときは写して、`docs/` `specs/` `context/` の該当箇所へ置きます。

| # | テンプレート | 置き場 | 必須の条件 | 関係するゲート |
| --- | --- | --- | --- | --- |
| 0 | [体制図(D-0)](./00-d0-governance.md) | `docs/D-0-governance.md` | **常に必須**(規模によらない) | G-1 の前提条件 |
| 1 | [機能仕様](./01-feature-spec.md) | `specs/F-NNN/spec.md` | **常に必須** | G-2 / G-4 |
| 2 | [判断記録(ADR)](./02-adr.md) | `context/decisions/NNNN-*.md` | 設計上の選択を伴った場合 | G-3、G-6(コア機能で添付) |
| 3 | [技術負債台帳](./03-debt-ledger.md) | `docs/debt-ledger.md` | 妥協・仮実装を受容した場合 | G-5 / G-7 |
| 4 | [ゲート判定記録](./04-gate-record.md) | `docs/gates/*.md` | **常に必須**(有効なゲートすべて) | 全ゲート |
| 5 | [運用引き継ぎ文書](./05-handover.md) | `docs/handover.md` | G-7 が有効なら必須 | G-7 |
| 6 | [企画書](./06-project-brief.md) | `docs/project-brief.md` | **常に必須** | G-1 |
| 7 | [実装計画](./07-implementation-plan.md) | `specs/F-NNN/plan.md` | **常に必須** | G-4 |
| 8 | [AI-SLA 合意確認書](./08-ai-sla.md) | `docs/ai-sla.md` | 委託契約がある場合 | G-7、契約添付 |
| 9 | [安全リスクアセスメント](./09-safety-risk-assessment.md) | `docs/safety-risk-assessment.md` | 下の4条件のいずれか | G-1 の前提条件 |
| 10 | [前提の台帳](./10-assumption-ledger.md) | `docs/assumptions.md` | **常に必須** | 全ゲートの通過条件 |

## テンプレ9 の適用条件

次のいずれかに該当する場合に必須です。

1. 物理的な危険源を持つ機器を制御する
2. エージェントの適用範囲に、取り消しに相手方の同意を要する変更種別(R1)を含む
3. エージェントが本番環境の資源へ到達する
4. AI 自律レベルが L2 以上

## 常に必須の6種

`process.config.json` の構成にかかわらず必要なものです。

- テンプレ0(体制図) — 人数が少ないほど兼務が増え、誰が決めるかが曖昧になるため
- テンプレ1(機能仕様)
- テンプレ4(ゲート判定記録)
- テンプレ6(企画書)
- テンプレ7(実装計画)
- テンプレ10(前提の台帳)

会議体は規模に応じて減らせます。**決定の権限と境界の記述は減らせません**。

## 参照

- [第6章 成果物テンプレート](https://takenori-kusaka.github.io/process-compass/phase4-process-design/deliverable-templates/)

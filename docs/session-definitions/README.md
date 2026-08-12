---
derived_from: docs/D-0-governance.md
d0_version: "1.1"
status: 草案(価値責任者が起草。AI 維持管理者の確定を待つ)
date: 2026-08-12
---

# ロール別セッション定義(草案)

## これは何か

`.claude/skills/{po,dev,qm,audit,platform}/SKILL.md` を **D-0 v1.1 から書き直すための草案**です。

現行の定義5件は日本語部分が二重エンコードで破損しており、内容を復元できません([#27](https://github.com/Takenori-Kusaka/Filetto/issues/27))。**復元ではなく再作成が要ります。**

## なぜここに置くか

**`.claude/**` は強制層で保護されており、エージェントから書き込めません。** `CLAUDE.md` は Bash 経由での迂回を禁じています。したがって草案を保護対象外の場所へ置き、**AI 維持管理者(人)が内容を確定して `.claude/skills/` へ配置します。**

## 配置の手順(AI 維持管理者)

```
1. 本ディレクトリの po.md / dev.md / qm.md / audit.md / platform.md の内容を確認する
2. Filetto-po/.claude/skills/{role}/SKILL.md へ UTF-8 で保存する
3. 同じ5ファイルを残り4レーンへ複製する
     Filetto-dev / Filetto-qm / Filetto-audit / Filetto-platform
4. 保存後、二重エンコードが混入していないことを確認する
     python -c "import sys;t=open(sys.argv[1],encoding='utf-8-sig').read();print(sum(t.count(c) for c in '蠖縺繧繝蜿'))" <file>
     0 以外なら保存経路のエンコード設定を疑う
```

**各レーンが5ロール分すべての定義を持ちます。** 引き渡し先の責務を知るために要るためです。「自分のロールの定義だけ置く」では足りません。

## 各定義に共通で入れているもの

| # | 項目 | 根拠 |
| --- | --- | --- |
| 1 | そのロールが判定者となるゲート | D-0 第1節 |
| 2 | **そのロールが実行してはならない工程** | D-0 第2節の抵触 / 第3節の未達 |
| 3 | 受信箱のポーリングコマンド | [Label Mailbox 4.5](https://takenori-kusaka.github.io/process-compass/phase5-implementation/label-mailbox/) |
| 4 | 引き渡し先のロールと使用するラベル | Label Mailbox 4.4 |
| 5 | 追随している D-0 の版番号(frontmatter) | 版ずれの機械検出のため |

**2 が現行の定義に無かったことが、本案件でロール越境が起きた原因の一部です。**

## 本案件に固有の前提(全ロール共通)

| # | 前提 |
| --- | --- |
| 1 | **1名(+AI)の体制**。兼務が多く、D-0 第2節に抵触2件がある |
| 2 | **独立レビュア(G-6)は不在。未達として記録済み**(省略ではない)。**AI を代替に置かない** |
| 3 | **市場・顧客仮説の検証は未達**(D-0 第3節) |
| 4 | **エスカレーション先は存在しない。** 判定の期限超過・判定者不在は、いずれも案件の停止と再計画(D-0 第5節) |
| 5 | **代行者は存在しない。** 価値判断・技術判断を AI へ代行させない(D-0 第6節) |
| 6 | 強制層で保護されたファイルはエージェントから書けない: `process.config.json` / `PROCESS-PROFILE.md` / `adapters/**` / `.github/workflows/**` / `.claude/**` |

## 二重エンコード検査を入れる際の除外

本ディレクトリの `README.md` と `platform.md` は、**検査すべき文字そのものを検査の仕様として本文に含みます。** 二重エンコードの検出を CI へ入れる際は、この2ファイルを除外してください。除外しない場合、検査の仕様を書いた文書が検査に落ちます。

## 未整備の項目

**本リポジトリに `state:needs-audit` と `state:needs-platform` のラベルが存在しません。** 標準は定義していますが、現状のラベルは6種のみです。Audit と Platform への引き渡しが表現できません。**Platform への依頼対象です。**

## 関連

- [#27](https://github.com/Takenori-Kusaka/Filetto/issues/27) 案件側の修復
- [pit-in-template#14](https://github.com/Takenori-Kusaka/pit-in-template/issues/14) テンプレート側の欠陥
- [process-compass#216](https://github.com/Takenori-Kusaka/process-compass/issues/216) D-0 から定義内容を導出する経路が標準にない

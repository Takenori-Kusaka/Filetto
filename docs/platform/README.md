# Platform レーンの記録と、強制層の変更手順

Platform は検査・リント・CI/CD の装置を作り、維持します。**判定は行いません。**

## 記録

| 番号 | 内容 |
| --- | --- |
| [PL-0001](PL-0001-ip-clearance-pep639.md) | `ip-clearance` の PEP 639 対応。SPDX 式の評価を自前へ移す |

## 強制層に触る変更をどう進めるか

次のファイルはエージェントから書けません。`.claude/guard.json` の `protectedPatterns` が遮断します。

```
.claude/settings.json  .claude/guard.json  .claude/hooks/**
.github/rulesets/**    .github/workflows/**
process.config.json    PROCESS-PROFILE.md
adapters/**            scripts/gate/**      scripts/vendor/**
CODEOWNERS             .github/CODEOWNERS
```

**この遮断は不具合ではありません。** エージェントが自分を縛る設定を変えられる構成では、遮断が成立しません。**Bash 経由での迂回もしません。**

そのうえで、変更のたびに手順を思い出す状態にはしません。**手順を固定します。**

### 手順

1. **Platform が変更内容を `docs/platform/proposed/` に置く。** 配置先と同じ名前にする(`proposed/license-check.mjs` → `scripts/gate/license-check.mjs`)
2. **Platform が検証結果を PL-NNNN として記録する。** 実測の出力を貼る。「通るはず」は書かない
3. **Platform がテストを `tests/` へ置く。** 強制層ではないため書ける。CI から必ず走る経路まで用意する
4. **人が適用する。** 適用コマンドは PR 本文に載せる。人がやることは「読んで貼る」だけにする
5. **適用後、`docs/platform/proposed/` から消す。** 正本が2箇所にある状態を残さない

### 適用コマンドの書き方

PR 本文へ、そのまま貼れる形で載せます。**何をどこへ置くかが1行で読めること。**

```bash
cp docs/platform/proposed/<name> <配置先>
git rm -r --cached docs/platform/proposed  # 適用後に proposed を畳む場合
```

## 既知の穴

| # | 内容 | 判断者 |
| --- | --- | --- |
| 1 | `.claude/settings.json` の `deny` に `Edit(./scripts/gate/**)` はあるが **`Write(./scripts/gate/**)` が無い**。`scripts/vendor/**` は両方ある。`guard.json` 側が塞いでいるため実害は出ていないが、二重の防護のうち片方が欠けている | **Owner**。エージェントは自分を縛る設定を変えません |

## 検査を足すときの原則

| # | 原則 |
| --- | --- |
| 1 | **検査が通ることと、正しいことは別である** |
| 2 | **黙って通る検査を作らない。** 対象が0件のときは、0件であることを出力する |
| 3 | 運用に依存する値を定数にしない(`context/standards/extensibility.md`) |
| 4 | 検査の追加・変更は、機能変更と混ぜない |
| 5 | **テストを置いたら、CI から走ることまで確かめる。** 置いただけのテストは検査ではない |

# PL-0013: CI の実効性を実測し、効いていなかった2件を直す

対象: 事業決裁者の問い(2026-08-14)「今運用されている CI って実効性ありますか？」
作成: 2026-08-14 / レーン: Platform

## 1. 実測 — 直近100実行、失敗14件を解析

| 検査 | 落ちた回数 | 出自 |
| --- | --- | --- |
| spec-lint | **5** | テンプレート(本案件で2回改修) |
| record-integrity | **4** | **本案件で設計** |
| test | 3 | テンプレート |
| pr-base-check | **2** | **本案件で設計** |
| static-analysis | 1 | テンプレート |
| external-host-check | **1** | **本案件で設計** |
| double-encoding-check / session-definition-drift / license-consistency / ip-clearance | 0 | 導入時に検出の実績あり |
| **secret-scan** | **0** | **実施していなかった** |
| dependency-diff / gate-contract / config | 0 | 合否を判定しない、または前提の確認 |

**0回は「効いていない」ではありません。** ip-clearance は導入時に `cryptography` を、session-definition-drift は2件を、license-consistency は README の MIT 誤記を、それぞれ検出しています。

## 2. 効いていなかった2件

### 2-1. `secret-scan` は実施していませんでした

```
$ node scripts/gate/adapter.mjs run secretScan
::notice::アダプタ python: "secretScan" のコマンドが空のため実施しません
exit=0
```

**`gate-g5.yml` 自身が「台帳記録による通過を認めない唯一の基準」と書いている検査**が、空のコマンドで通過していました。`verify-gate-contract` は警告を出していましたが、**合否には影響しません。**

**直近100実行で0回落ちたのは、検査が通っていたからではなく、検査していなかったからです。**

#### 直したこと

| 変更 | 内容 |
| --- | --- |
| `adapters/python.json` | `secretScan` に `detect-secrets` を書いた |
| `scripts/gate/secret-scan-check.mjs`(新規) | 判定部。**入力が空なら落とす** |
| `scripts/gate/secret-scan-policy.json`(新規) | 除外パスと、理由つきの許可一覧 |
| `pyproject.toml` | `detect-secrets>=1.5` を dev 依存へ |
| `.github/workflows/gate-g5.yml` | secret-scan の `install: 'false'` を外した |

```
検査した規則: 27 件
検出したファイル: 0 件
理由を添えて除外したもの: 0 件
秘匿情報の疑い: 0 件
```

**道具を dev 依存へ入れたのは、ip-clearance の対象にするためです。** 検査の道具のライセンスを検査しない状態を作りません(`detect-secrets` は Apache Software License。許可範囲内)。

**入力が空なら落とします。** 道具が動かなかったことを合格として記録しません。**これが本件で起きたことそのものです。**

### 2-2. カバレッジ閾値 90% は何も保証していませんでした

```
カバレッジ 100.0%  対象行 2
```

実装コードは `src/filetto/__init__.py` の10行で、statements は **2**。**2行のうち2行が通れば 100%** です。

#### 直したこと

**測定対象が下限に達しない間は、判定を実施しません。実施しなかったことを出力し、証跡へ残します。**

```
::notice::カバレッジの判定を実施しません。測定対象が 2 文で、判定を始める下限 50 文に
達していません(実測 100%)。この状態では下限 90% は品質について何も述べません
```

```json
{ "measured": false, "pct": 100, "threshold": 90, "statements": 2, "minStatements": 50 }
```

**「通過した」と「判定していない」を区別できる形にします。** 従来は `measured: true` として100%が記録され、**閾値を満たしたように読めていました。**

**閾値を下げていません。** 90% のままです。**下げるのは検証の放棄です**(Platform の禁止2)。

## 3. 切り替えの条件は暫定です

**statements の数で切り替えているのは暫定の措置です。**

**本来は「どのフェーズから実装向けの検査を有効にするか」をプロセスの構成が定めるべきです。** `process.config.json` にも標準にもその欄がありません。

| いま | あるべき姿 |
| --- | --- |
| `ci.coverageMinStatements: 50` | 構成が「S2 以降はカバレッジを合否条件にする」と定める |
| Platform が数値を決めた | **フェーズの定義は標準の領域** |

**process-compass へ起票します。** 欄ができたら、そちらへ差し替えます。

## 4. 構造的な発見

**テンプレートの検査は「プロダクトのコードがある」前提で設計されています。**

| 検査 | いま守っているもの |
| --- | --- |
| test(135件) | **ほぼ全部が `tests/gate/`。検査の装置のテスト** |
| coverage / static-analysis / ip-clearance | 実装2文と開発依存 |
| **実際に落としているもの** | **spec-lint・record-integrity・pr-base-check・external-host-check** |

**S1(価値確立)段階で検証対象になっているのは実装ではなく記録です。**

**そして記録を検査する仕組みは標準にありません。** 本案件が事故のたびに足したものです(PL-0002〜0012)。

## 5. 未実行のワークフロー

| ワークフロー | 実行記録 | 評価 |
| --- | --- | --- |
| `context-drift` | **0件** | 週次 cron。**動いていません** |
| `ship-evidence` | 0件 | タグ `v*` push のみ。**設計どおり**(タグが無い) |
| `gate-entry` | 20/20 success | D-0 の存在確認。落ちる余地が小さい |

**`context-drift` は別途調べます。** 本 PR の範囲外です。

## 6. 検証

```
$ node scripts/gate/adapter.mjs run secretScan → 27 規則で検査、0 件検出 (exit 0)
$ node scripts/gate/coverage-check.mjs         → 判定を実施しません(証跡へ measured: false)
$ node scripts/gate/verify-gate-contract.mjs   → 注意 2 件 → 1 件へ減少
$ pytest tests/gate                            → 135 passed
$ ruff / spec-lint / record-integrity / ip-clearance → 緑
```

否定側:

| # | 確かめたこと | 結果 |
| --- | --- | --- |
| 1 | **秘匿情報を検出すれば落ちる** | 落ちた |
| 2 | **入力が空なら落ちる**(本件の事象) | 落ちた |
| 3 | JSON でなければ落ちる / `results` が無ければ落ちる | 落ちた |
| 4 | 理由を添えた除外は通り、理由が出力される | 通った |
| 5 | **アダプタの `secretScan` が空でない** | 通った |
| 6 | 測定対象が下限未満なら判定を実施しない | 通った |
| 7 | **実施しなかったことが証跡に残る** | 通った |
| 8 | **下限以上で閾値を下回れば落ちる**(実施しない仕組みが抜け道にならない) | 落ちた |

## 7. 参照

- `docs/platform/README.md` — 検査を足すときの原則
- [#58](https://github.com/Takenori-Kusaka/Filetto/issues/58) 運用上の注意1 — `secretScan` が空である記録
- [PL-0001](PL-0001-ip-clearance-pep639.md)〜[PL-0012](PL-0012-record-integrity.md) — 本案件が足した記録の検査

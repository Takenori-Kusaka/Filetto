# プロセス構成書

このファイルは `/process-init` が生成しました。**手での直接編集は行わず、調達先の記入は `node scripts/init/set-review-sourcing.mjs` を使用してください**。
構成を変えるときは `/process-init` を再実行してください。

- 案件 ID: `P-001`
- 生成日時: 2026-08-13T12:06:21.598Z
- 機械可読の構成: [`process.config.json`](./process.config.json)

## 未達のゲート

次のゲートは、**目的を達成する構成を示せていません**。省略ではありません。

| ゲート | 未達の理由 | 代償措置 | 外部レビューの調達先 | 根拠 |
| --- | --- | --- | --- | --- |
| G-6 独立レビュー | 作成を指示した本人以外が挙動を確認する条件を満たす構成が存在しない(最小体制3名未満、かつ外部のレビュアが不在) | ci-strict / post-release-audit | **未記入** | [ADR-0028(未達と省略の区別)](https://takenori-kusaka.github.io/process-compass/adr/0028-unmet-gate-distinct-from-omitted/) |

### G-6 独立レビュー を AI で埋めない理由

同一のモデルを用いる限り、エージェントを分けても事前学習の知識という共通の原因が残る。生成物の確認を生成器へ委ねる構成は自動化バイアスによって見落としを増やす

埋める方法:

- リポジトリを公開し、コミュニティのレビューを受ける
- 他の個人開発者と相互レビューの取り決めをする
- 有償のコードレビューを利用する
- 体制が3名以上になったら /process-init を再実行する

調達先が決まったら、次のコマンドを実行して記入してください。
```bash
node scripts/init/set-review-sourcing.mjs --gate g6 --sourcing "ここに調達先を記入"
```

未記入のまま運用している状態は、出荷判定の証跡にも残ります。

## 代償措置つきの逸脱

次のゲートは**実施しますが、標準が要求する属性を欠いています**。未達ではありません。

| ゲート | 抵触する規則 | 欠けるもの | 解消の時点 | 根拠 |
| --- | --- | --- | --- | --- |
| G-7 出荷判定 | 開発ライン × 出荷判定者(同一案件)の兼務の禁止(第3章 3.5) | 3名未満の体制では、開発ラインから独立した出荷判定者を置けない。判定と基準の突合は単独で実行できるため未達ではないが、判定者の独立性は失われる | 体制が3名以上になり、開発ラインの外から出荷判定者を置けるようになった時点 | [第3章 3.5.2 / ADR-0029](https://takenori-kusaka.github.io/process-compass/adr/0029-shipping-approver-merge-exception/) |

### G-7 出荷判定 の代償措置

次をすべて満たす場合に限り、この構成で運用できます。

- [ ] G-7 の判定記録を必須とし、基準の各項目との突合を記録に残す
- [ ] リリース後の抜き取り確認を定常作業として置く
- [ ] 兼務の事実と代償措置を D-0 体制図へ明記する

**代償措置は独立性の回復ではありません**。判定が甘くなる可能性は残ります。記録と抜き取りが行うのは、甘さを後から検出できる状態にすることだけです(第3章 3.5.2 / ADR-0029)。

## 事業ステージとステージ移行ゲート(SG)

標準プロセスには、開発の工程ゲート(G-1〜G-8)とは別に、投資継続を判断する**ステージ移行ゲート(SG-0〜SG-2)**が定義されています。

| ステージ | 目的 | 移行ゲート | 対象とする状態 |
| --- | --- | --- | --- |
| **S0 探索** | 事業仮説と技術的実現性の検証 | **SG-0** | 技術的実現性が確認され、次ステージの投資・体制が示されている |
| **S1 構築** | 最初の顧客向け(MVP)の構築とビジネス検証 | **SG-1** | 期待効果の検証、初期顧客の獲得、継続的な開発体制の確立 |
| **S2 拡大・運用** | プロダクトの成長、組織拡大、安定運用 | **SG-2** | 投資対効果の最大化、非機能要件 of ... |

### 現在のステージ判定と確認

- **現在の想定ステージ**: `S1 構築` (最初の顧客向け(MVP)段階)
- **通過済みの前提**: **SG-0** (技術的実現性の確認)
- **目指すゲート**: **SG-1** (ビジネス実証)
- **注意**: 技術的実現性(採用技術が自社ドメインで実用精度を出すことなど)が未検証のまま MVP 工程に入ると、大きな手戻りリスクがあります。**「まだ一度も技術的実現性を検証していない(SG-0を通せる状態にない)」場合は、実態は S0 探索ステージです。** その場合、先に PoC(検証中) として `/process-init` を再実行し、SG-0 を目指すことを強く推奨します。

## あなたの状況

| 軸 | 回答 |
| --- | --- |
| A. チーム規模 | 1〜2名 |
| B. 事業ステージ | 最初の顧客向け(MVP) |
| C. 期待品質・規制 | 止まると社会・金銭に影響する |
| D. 開発形態 | 自社開発 |
| E. 安全重要度 | 経済的な損失や業務の中断にとどまる |
| 外部のレビュア | いない |
| 既存の承認ゲート | ない |
| AI 利用の制約 | 制約なし |

成熟度やスコアは出しません。評価ではなく構成の導出です。

## 標準からの差分

標準どおりの項目も省かずに載せます。載っていない項目があると、検討したのか漏れたのかを区別できません。

| ゲート | 判定 | 判定者 |
| --- | --- | --- |
| [G-1 企画承認](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-1-企画承認事業決裁者既存規程どおり) | 適用する | 事業決裁者(決裁権限規程どおりの職位) |
| [G-2 要件合意](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-2-要件合意価値責任者48時間) | 適用する | 価値責任者(単独。目安48時間以内に判定) |
| [G-3 技術設計判断](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-3-技術設計判断技術判断者48時間) | 適用する | 技術判断者(単独。目安48時間以内に判定) |
| [G-4 機能仕様承認(反復内)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-4-機能仕様承認価値責任者または委譲先24時間) | 適用する | 価値責任者(または明示的に委譲された機能責任者。委譲しても結果責任は価値責任者に残る) |
| [G-5 自動検証(CI)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-5-自動検証-ci機械判定即時) | 適用する | CI(機械判定) |
| [G-6 独立レビュー](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-6-独立レビュー独立レビュア応答1営業日--判定2営業日) | **未達** | 独立レビュア(作成指示者本人は承認不可。ブランチ保護で強制) |
| [G-7 出荷判定](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-7-出荷判定qa3営業日) | 適用する | 価値責任者(出荷判定者を兼務。代償措置つきの逸脱) |
| [G-8 リリース決裁](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/#g-8-リリース決裁事業決裁者48時間) | 適用する | 事業決裁者 |

ゲート名は標準の該当節へのリンクです。**構成の根拠は標準にあります**。

## ロールの構成

**役割の割り当てを人へ書いただけでは、実行主体には届きません**。各セッション・作業領域は、自分が判定してよいゲートと、担ってはならない工程を起動時に参照してください(標準 第3章 3.5.3)。この表は兼務禁止表から導出したものです。**手で編集しないでください**。

- 追随している D-0 体制図の版: `1.4`

| ロール | 判定するゲート | 兼ねてはならない役割 | 判定してはならないゲート |
| --- | --- | --- | --- |
| [価値責任者(Value Owner)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-2 / G-4 / G-7。G-7 を兼務する(代償措置つきの逸脱。判定記録と抜き取り確認を要する) | — | — |
| [技術判断者(Tech Lead)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-3 | — | — |
| [開発者(検証者)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | — | 独立レビュア / 品質保証(出荷判定者)(例外あり) | G-6 / G-7 |
| [AIエージェント](https://takenori-kusaka.github.io/process-compass/phase4-process-design/human-ai-boundary/) | — | — | G-1 / G-2 / G-3 / G-4 / G-5 / G-6 / G-7 / G-8 |
| [独立レビュア](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-6(**未達**) | 開発者(検証者) | — |
| [品質保証(出荷判定者)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | この構成では分離できていない。判定は価値責任者が兼ねる | 開発者(検証者)(例外あり) | G-7 |
| [事業決裁者](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-1 / G-8 | — | — |
| [コンテキストオーナー](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | — | — | — |
| [AI維持管理者(AI Maintainer)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | — | AI運用担当者(AIOps) | — |
| [AI運用担当者(AIOps)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | — | AI維持管理者(AI Maintainer) | — |

**起案した主体は、その成果物の判定者になりません**。役割の組み合わせによらず成立しない禁止です。分離は、作業領域・セッション・認証情報の3つがすべて分かれている場合にのみ成立します。

## 各判定の理由

### G-5 自動検証(CI)

- 代替としてCI基準を厳格化する(カバレッジ+静的解析の基準を引き上げ)

### G-6 独立レビュー

- 独立レビューは実施できないため省略する

### G-7 出荷判定

- 出荷判定は価値責任者が兼ねる。ただし判定記録は必ず残す
- 出荷判定に限定的な抜き取り確認を追加する
- 設定: `approverMode` = `value-owner-merged`

## 外せない下限

どの構成でも、次は調整で外せません。

- **結果責任は1人** — A(結果責任)を2人以上に割り当てない
- **AIは責任者になれない** — AIをA(結果責任)に割り当てない。AIはどこまでもR(実行)
- **ゲートには差し戻し基準** — 差し戻し基準(チェックリスト)のないゲートを作らない
- **安全関連部の自律度はL1** — 安全重要度CL3の安全関連部で、AI自律レベルをL1より上げない
- **安全リスクアセスメントは省略しない** — 安全重要度CL2以上で、安全リスクアセスメント(テンプレ9)と安全適合性の検証記録を省略しない
- **調整は宣言する** — 標準から外した項目を、理由と承認者とともに提案書へ記載せずに運用しない

- **G-4(機能仕様承認)と G-5(自動検証)はどのステージでも省略できない**

## CI の設定値

| 項目 | 値 |
| --- | --- |
| カバレッジの下限 | 90% |
| 失敗させる重大度 | critical / high |
| 許可するライセンス | MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, PSF-2.0, AGPL-3.0-or-later, MIT License, Apache Software License, BSD License, Apache-2.0 OR BSD-2-Clause, Mozilla Public License 2.0 (MPL 2.0), Python Software Foundation License |
| 必須の承認数 | 0 |
| アダプタ | `python` |

カバレッジの下限は初期値です。**実測に基づく値ではありません**。企画承認(G-1)で自組織の値を定めて置き換えてください。

### 実装スタックの確定時期

**実装スタックは探索ステージ(S0)の出力であり、入力ではありません**。アダプタが `none` のままでも構成を初期化してかまいません。

| 時点 | 扱い |
| --- | --- |
| S0 の期間中 | 未確定でよい。**未確定は未達ではない** |
| SG-0 の判定時 | 確定させる。判定基準「技術的実現性が確認されている」に含む |
| SG-0 の通過後 | 未確定が残る場合は未達として扱う |

記録済みのスタックを S0 の結果に基づいて変更する場合は、**技術判断者の判断とし、判断記録(ADR)を残します**。企画承認の判定基準は実装スタックを含まないため、**G-1 の再判定は要しません**。

## 構成を変える

- 体制・ステージが変わったら `/process-init` を再実行する
- **厳しくする方向の変更は自由**。緩める方向の変更は、理由を判断記録(`context/decisions/`)へ残す
- 個別の値だけを変える場合は `process.config.json` を編集し、CI の契約検査を通す

```bash
node scripts/gate/verify-gate-contract.mjs
```

## 規則の衝突

- gate:g-ship への「simplify」を優先度の高い規則が「strengthen」で上書き
- gate:g-indep-review の省略により設定「scope」が無効化
- gate:g-indep-review の省略により設定「reviewMode」が無効化
- gate:g-indep-review の省略により設定「coreReviewerCount」が無効化

## 根拠

この構成は [ピットイン方式 第8章 テーラリング](https://takenori-kusaka.github.io/process-compass/phase4-process-design/tailoring-guide/) の規則から導出しました。

適用した規則: `r-b-mvp`, `r-s-no-existing-gates`, `r-a-solo`, `r-c-high`, `r-s-no-external-reviewer`

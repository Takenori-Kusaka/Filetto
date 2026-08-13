# このリポジトリの開発規約

このプロジェクトは**ピットイン方式**(正式名称: AI協調型ソフトウェア開発プロセス標準)で開発します。

> マシンは人間より速い。それでも、決められた場所では必ず人間が触る。

## まず読むもの

| ファイル | 中身 |
| --- | --- |
| `PROCESS-PROFILE.md` | このプロジェクトのプロセス構成と、標準からの差分 |
| `process.config.json` | 機械可読の構成。**有効なゲートはここが正本** |
| `context/glossary.md` | ドメイン用語 |
| `context/standards/` | 設計標準・レビュー観点 |
| `context/decisions/` | 判断記録(ADR) |

`PROCESS-PROFILE.md` が未設定の場合、まず `/process-init` の実行を人へ促してください。プロセス構成が決まる前に 実装を始めないでください。

<!-- generated:process-rules start -->

## このプロジェクトの構成(自動生成)

この節は `process.config.json` から生成しています。**手で編集しないでください**。内容を変えるときは `/process-init` を再実行します。手で編集すると `check-process-rules` が失敗します。

- 案件 ID: `P-001`
- 追随している D-0 体制図の版: `1.4`

### 有効なゲートと判定者

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

**判定の基準を確認するときは、ゲート名のリンク先(標準の該当節)を読んでください**。

**未達のゲート**: G-6 独立レビュー(作成を指示した本人以外が挙動を確認する条件を満たす構成が存在しない(最小体制3名未満、かつ外部のレビュアが不在))

未達は省略ではありません。**AI で埋めてはなりません**。

**代償措置つきの逸脱**: G-7 出荷判定(開発ライン × 出荷判定者(同一案件)の兼務の禁止(第3章 3.5))

### ロールごとの権限

**自分がどのロールのセッションかを確認してから作業を始めてください**。
分離は、作業領域・セッション・認証情報の3つがすべて分かれている場合にのみ成立します(標準 第3章 3.5.3)。

| ロール | 判定するゲート | 判定してはならないゲート | 受信箱 | 引き渡しに使うラベル |
| --- | --- | --- | --- | --- |
| [価値責任者(Value Owner)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-2 / G-4 / G-7。G-7 を兼務する(代償措置つきの逸脱。判定記録と抜き取り確認を要する) | — | `state:needs-po` | `state:needs-dev` `state:needs-tech` `state:needs-audit` `state:needs-platform` `state:needs-owner` |
| [技術判断者(Tech Lead)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-3 | — | `state:needs-tech` | `state:needs-dev` `state:needs-po` `state:needs-owner` |
| [開発者(検証者)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | — | G-6 / G-7 | `state:needs-dev` `state:qm-blocked` | `state:dev-done` `state:needs-po` `state:needs-tech` `state:needs-owner` `state:needs-platform` |
| [独立レビュア](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-6(未達) | — | `state:dev-done` | `state:qm-blocked` `state:ready-to-merge` |
| [品質保証(出荷判定者)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | この構成では分離できていない。判定は価値責任者が兼ねる | G-7 | `state:dev-done` `state:ready-to-merge` | `state:qm-blocked` `state:ready-to-merge` |
| [事業決裁者](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | G-1 / G-8 | — | `state:needs-owner` | `state:needs-po` `state:needs-dev` |
| [AI維持管理者(AI Maintainer)](https://takenori-kusaka.github.io/process-compass/phase4-process-design/roles-responsibilities/) | — | — | `state:needs-platform` | `state:dev-done` |

- **起案した主体は、その成果物の判定者になりません**。役割の組み合わせによらない禁止です
- **自分のロールの受信箱以外を拾わないでください**。ディレクトリが分かれていても、複数のレーンの受信箱を見た時点で文脈は合流します
- エージェント指示資産(強制層。`.claude/**`)の統合・削除は AI維持管理者へ集約します。変更が必要な場合は `state:needs-platform` を付与します([第5章 Label Mailbox](https://takenori-kusaka.github.io/process-compass/phase5-implementation/label-mailbox/))

#### 標準の条項を課す前に、適用範囲を確認する

**条項番号だけを根拠にしないでください**。適用範囲を書けない条項は課さないでください。箇条書きだけを読んで限定を落とすと、適用されない条項を課すことになります([適用範囲の書き方](https://takenori-kusaka.github.io/process-compass/community/scope-marking/))。

| 条項 | 適用範囲 | 判定の単位 |
| --- | --- | --- |
| [AIエージェント安全リスクアセスメント](https://takenori-kusaka.github.io/process-compass/phase4-process-design/deliverable-templates/#aiエージェント安全リスクアセスメント適用-物理的な危険源r1-の変更種別本番到達l2-以上のいずれか) | 物理的な危険源・R1 の変更種別・本番到達・L2 以上のいずれか | **変更ごと** |
| [5.7.3 選択肢の比較](https://takenori-kusaka.github.io/process-compass/phase4-process-design/human-ai-boundary/#573-選択肢の比較適用-r1-の決定例外承認) | R1 の決定・例外承認 | **変更ごと** |

**リスク区分(R)は変更ごとに判定します**。この案件の安全重要度から「適用されない」を導いてはなりません。CL0 の案件でも、認証・認可・個人データ・外部インタフェースに触れる変更は R1 です。

#### 統制の弱化を見つけたら

**遮断の解除・閾値の緩和・強制層の縮小**を見つけた場合は、差分が変更の主張と一致するかまでを確認し、**許容してよいかは判断しないでください**。

| 対象 | 付与するラベル |
| --- | --- |
| 強制層(`.claude/**` 等)の縮小 | `state:needs-platform` |
| 不可逆4操作に該当する(ガード・検証ゲート・重要テストの削除を含む) | 上に加えて `state:needs-owner` |
| 弱化の範囲そのものの適否 | `state:needs-po` |

**引き渡し先が分からないことを、自分で決める理由にしないでください**。特定できない場合は `state:needs-po` を付与します。兼務していても、ラベルを経由させて引き渡しを記録します([第5章 4.7](https://takenori-kusaka.github.io/process-compass/phase5-implementation/label-mailbox/))。

**規定の全文は標準にあります**。判断に迷ったら、表のリンク先を読んでから進めてください。推測で補わないでください。

- **開発者(検証者)** が兼ねてはならない役割: 独立レビュア / 品質保証(出荷判定者)(例外: 3名未満に限り、代償措置つきで兼務を認める(第3章 3.5.2 / ADR-0029))
- **独立レビュア** が兼ねてはならない役割: 開発者(検証者)
- **品質保証(出荷判定者)** が兼ねてはならない役割: 開発者(検証者)(例外: 3名未満に限り、代償措置つきで兼務を認める(第3章 3.5.2 / ADR-0029))
- **AI維持管理者(AI Maintainer)** が兼ねてはならない役割: AI運用担当者(AIOps)
- **AI運用担当者(AIOps)** が兼ねてはならない役割: AI維持管理者(AI Maintainer)

### 自分の受信箱を見る

**自分のロールのブロックだけを実行してください**。他のロールの受信箱を見た時点で文脈は合流し、分離は成立しなくなります([第5章 4.5.1](https://takenori-kusaka.github.io/process-compass/phase5-implementation/label-mailbox/))。

```bash
# 価値責任者(Value Owner)
gh issue list --label "state:needs-po" --state open
gh pr list --label "state:needs-po" --state open

# 技術判断者(Tech Lead)
gh issue list --label "state:needs-tech" --state open
gh pr list --label "state:needs-tech" --state open

# 開発者(検証者)
gh issue list --label "state:needs-dev" --state open
gh pr list --label "state:needs-dev" --state open
gh issue list --label "state:qm-blocked" --state open
gh pr list --label "state:qm-blocked" --state open

# 独立レビュア: この構成では未達。担い手がいないため受信箱を置かない

# 品質保証(出荷判定者)
gh issue list --label "state:dev-done" --state open
gh pr list --label "state:dev-done" --state open
gh issue list --label "state:ready-to-merge" --state open
gh pr list --label "state:ready-to-merge" --state open

# 事業決裁者
gh issue list --label "state:needs-owner" --state open
gh pr list --label "state:needs-owner" --state open

# AI維持管理者(AI Maintainer)
gh issue list --label "state:needs-platform" --state open
gh pr list --label "state:needs-platform" --state open
```

状態ラベルの付いていない Issues/PRs(孤児)の再配分は価値責任者の義務です。**再配分した仕事を自ら拾わないでください**。再配分の権限と、仕事を拾う権限は別です。

### エスカレーションの段階とラベル

| 段階 | 報告先 | 付与するラベル |
| --- | --- | --- |
| 段階1 | プロジェクト責任者 | `state:needs-po` |
| 段階2 | 部門責任者・PMO | `state:needs-owner` |
| 段階3 | ステアリングコミッティ(B-2) | `state:needs-owner` |
| 不可逆4操作 | オーナー(事業決裁者) | `state:needs-owner` |

発火条件と閾値は[第7章 7.6](https://takenori-kusaka.github.io/process-compass/phase4-process-design/exception-escalation/)、実際の宛先は D-0 体制図の第4節によります。**ラベルの付与だけで報告を済ませないでください**。エスカレーションレポートの5項目(状態・原因・事業影響・リカバリ選択肢3案・推奨と決裁事項)を書きます。**推奨と決裁事項は人が記入します**。

<!-- generated:process-rules end -->

## 作業の進め方

1機能あたりのサイクルは次のとおりです。

```
受入基準を書く → タスクへ分解 → AI が実装 → 自動検証(G-5) → 人が差分を検証 → 記録を書き戻す
                                    ↑______不合格______|
```

工程3と工程4の往復は自律的に回します。工程1・2・5・6には人が関与します。

対応するスキル:

| スキル | 使う場面 |
| --- | --- |
| `/spec-write` | 受入基準を EARS 記法で書く |
| `/task-breakdown` | 実装計画へ分解する |
| `/implement` | 実装と自己修正ループ |
| `/human-verify` | 人が差分を検証する手順を提示する |
| `/gate-record` | ゲート判定を記録する |
| `/adr-write` | 設計判断を記録する |

### ロール間非同期メッセージング（Label Mailbox 連携）

物理隔離された各ロール（PO, Dev, QM, Audit, Platform）は、直接の同期通信や割り込み（指示を直接仰ぐ行為）を行わず、GitHubラベルをメッセージバスとした非同期・ポーリングベースの連携（[Label Mailbox仕様](https://takenori-kusaka.github.io/process-compass/phase5-implementation/label-mailbox/)）を使用する。

- 開発に着手した際、Draft PR の状態では **`state:needs-dev`** ラベルを維持すること。
- 実装・単体テスト（CI緑）が完了し、`human-verify` 用手順を提示する際、開発者（Dev）は `state:needs-dev` を剥がし、**`state:dev-done`** ラベルを付与して出荷判定者（QM）へ引き渡すこと。
- 独立レビューにおいて差し戻し（`state:qm-blocked`）が発生した場合、Devは対応を最優先する。対応が完了しCIが全緑になったら、必ず `state:qm-blocked` を剥がして再度 **`state:dev-done`** に戻すこと（復路の徹底）。
- 仕様や優先度の判断が不十分な場合、または不可逆4操作（削除/本番デプロイ/課金書き込み/スキーマ変更）が必要になった場合は、自走を停止し、**`state:needs-po`** または **`state:needs-owner`** を付与して人間（PO/Owner）の判断を待つこと。

直接の指示やメッセージを待つのではなく、定期的に自分のメールボックス（`gh` polling コマンド）を自律的に監視し、仕事を拾って処理すること。

### ロール別のレビュー視点

**各ロールが見る観点を固定します。** 暗黙にすると、同じ成果物を複数のロールが同じ観点で見て、**誰も見ていない観点が残ります**。

| ロール | 固定する視点 | 具体的な問い |
| --- | --- | --- |
| PO | **価値・優先順位・範囲** | 顧客にとって意味があるか。いまやる理由は何か。**作らないと決めたことの根拠は正しいか** |
| Dev | 実装可能性 | この記述のまま実装に落とせるか |
| QM | 出荷判定・検証可能性 | 後で顧客・監査に説明できるか。受入基準は検証可能な形で書かれているか |
| Audit | セキュリティ基準・プロセス標準への準拠 | この変更は基準に照らして許容範囲か |
| Platform | 基盤・再現性 | CI・環境に依存せず再現できるか |

**視点は分担であって、担当外を見てはならないという意味ではありません。** 気づいたことは誰でも報告します。**固定するのは「必ず見る」側だけです。**

### 統制の弱化を検知したときの引き渡し

**統制・認証認可・不可逆な運用ルールに関わる変更**（遮断の解除、閾値の緩和、強制層の縮小など）を検知した場合、次のとおり扱います。

| # | 手順 |
| --- | --- |
| 1 | 検知した者は**事実確認までに留める**（差分が PR の主張と一致するか） |
| 2 | 許容可否の判断は **`state:needs-audit`** を付与して Audit へ引き渡す |
| 3 | **同時に PO へも知らせる**（コメントでの言及で足りる） |

**判定はファイルパスではなく変更の性質で行います。** パスで定義すると、パスを増やすたびにルールの改訂が要り、**パスの定義そのものが誤っていた前例があります**。

**3 を省略しないでください。** 遮断を外すかどうかは Audit の基準準拠の判断ですが、**「その範囲でよいか」は範囲の決定であり PO の職務です**。Audit が単独で許容可否を決めると、範囲の決定が Audit へ移ります。

## 委譲できないもの

次の判断は AI が担いません。**自律レベルにかかわらず変わりません**。

- 何を作るか、どの順序で作るか(価値判断)
- どの設計を採るか、何を捨てるか(技術判断)
- 成果物が仕様どおり動くかの確認(理解の確認)
- 判断と検証の記録が完備しているかの確認(記録の確認)
- 認証・認可・個人データ・外部との契約に関わる変更
- 適用範囲そのものの拡大

結果責任(A)は常に人に紐づきます。AI は実行(R)だけを担います。

## 行ってはならない作業

| # | 禁止事項 | 理由 |
| --- | --- | --- |
| 1 | 受入基準を確定せずに実装を始める | 何をもって完了とするかが不定になる |
| 2 | AI が生成した受入基準をそのまま承認する | 価値判断を委譲したことになる |
| 3 | **テストの失敗を、テスト側の変更で解消する** | 検証の放棄であり、実装の完了ではない |
| 4 | 差分を確認せずに承認する | 独立レビューの前提が崩れる |
| 5 | **独立レビューの挙動要約を AI に生成させる** | 要約は理解の証拠であり、生成物は証拠にならない |
| 6 | カバレッジ閾値・静的解析の重大度・除外設定を機能変更と同じ PR で変える | 以後のすべての通過を無効化する |
| 7 | **`state:*` ラベルを貼らず、コメントや `@mention` だけで判断依頼や引き渡しを済ませる** | 相手の polling クエリに現れず、すべての受信箱から消えてタスクが滞留（orphan化）するため |
| 8 | **差し戻し（`qm-blocked`）対応後に、そのラベルを剥がし忘れる、または `dev-done` を貼り忘れる** | 復路の伝達が不完全となり、QMの受信箱に現れずプロセスが完全停止するため |

禁止事項3は、**2026-08-13 時点では機械で遮断していません**。序盤フェーズの間、強制層の遮断をすべて外しているためです([ADR-0015](context/decisions/0015-enforcement-scope-during-optimization.md))。**この期間、禁止事項3 は本文書とロール定義の遵守だけで保たれています。**

## 受入基準の書き方

「条件 + 期待動作」の形で書きます。次の語は使いません。

```
適切に / 柔軟に / 可能な限り / 〜など / 必要に応じて / 基本的に
```

これらは CI の `spec-lint` で検出し、G-5 を失敗させます。

完了の条件を曖昧さなく書けない機能は、書けるところまで分解してから実装へ渡します。エージェントが停滞する原因の 多くは能力の不足ではなく、完了条件の不在です。

## タスクの粒度

1タスク = 1レビュー単位に収めます。既定値は次のとおりです。

| 項目 | 目安 | 上限 |
| --- | --- | --- |
| 変更行数 | 100行 | 400行 |
| 変更ファイル数 | 10未満 | 15 |
| レビュー所要時間 | — | 30分で読み切れること |

1つの変更に複数の関心事を混ぜません。上限を超える場合は実装計画へ差し戻します。

### 行数上限を何に適用するか

**この既定値は、逐行読解しか手段がない場合の値です。数える対象は実装コードの差分です。**

行数の算定から次を除外します。

- 自動生成ファイル・ロックファイル・一括整形
- 機械的な変換。ただし「決定論的である」「テストで正しさを検出できる」「部分的に取り消せる」の3点を満たすものに限る

**判断記録(ADR)・機能仕様・設計文書には行数上限を適用しません。レビュー所要時間(30分で読み切れること)で判定します。**

ADR は「採らなかった選択肢とその理由」を含めることを求めています。行数に合わせて分割すると**1つの判断が複数ファイルに割れ**、後任者が「なぜそう決めたか」を追う経路が壊れます。行数に合わせて削ると、**削られるのは検討した選択肢の記録**になります(決定そのものは削れないため)。どちらも記録としての価値を損ないます。

ADR の分量の業界的な目安は1〜3ページであり、可変であることが明示されています。行数上限を適用している事例は確認されていません。

### この数値は暫定です

上限400行は**2006年の調査**(2,500件のレビュー・320万行)に由来します。原典が測ったのは**レビューの継続時間と欠陥検出率の関係**であり、行数上限そのものを検証した測定ではありません。成立の前提は当時のC系プロダクトコードとツール支援レビューで、**2010年代以降に独立して再検証した研究は確認されていません**(標準本文の暫定マーク EV-0005 / 根拠の水準 E1 / 見直し 2027-08)。

ファイル数(10 / 15)には数値自体の実証がありません。**区切り位置は自組織で較正する対象です。**

**運用開始後は自組織の実測へ置き換えます。** レビュー1件あたりの所要時間と変更規模を記録し、四半期ごとに、判定完了時間が基準を満たした変更の分布の上側パーセンタイル(初期は第85)を新しい上限とします。差し戻し率・リバート率・本番インシデント率が悪化していないことを併せて確認し、悪化していれば上限を戻します。**この手続を自動化してはなりません。**

詳細は[第4章 変更単位の水準](https://takenori-kusaka.github.io/process-compass/phase4-process-design/gate-criteria/)を参照してください。

### 分割しすぎない

小さくすることと、意味を成さないほど切り刻むことは別です。次を満たさない分割を認めません。

- 各変更が単独で意味を持ち、それだけでビルドと自動検証(G-5)が通る
- 新しいインタフェースを追加する変更は、その利用箇所を同じ変更に含める

## 自己修正ループ

自動検証の失敗を入力として修正を反復します。

- 反復回数の上限は3回(既定値)
- 上限に達したら人が受入基準へ戻る。実装の再試行を続けない
- **書き込み範囲にテストを含めない**。テストの修正を要すると判明したらループを終了する
- 同じ失敗を3回繰り返す場合、原因は実装ではなく受入基準の不備であることが多い

## ブランチとコミット

- トランクベース。`main` は常にリリース可能な状態を保つ
- ブランチ名: `feature/<機能ID>-task-<N>` / `fix/<Issue番号>-<内容>` / `docs/<内容>` / `chore/<内容>`
- コミット種別: `feat` `fix` `docs` `test` `refactor` `chore` `ci`
- コミットトレーラ: `Spec: F-012 / Task-3`(必須)、`ADR: ADR-021`(該当時)、`Co-Authored-By:`(AI が関与した場合は必須)
- コミットの Author は指示した人間。マージは squash

## 文脈への書き戻し

サイクルの終わりに次を記録します。

- 設計上の選択を伴った場合は ADR(`context/decisions/`)。**採らなかった選択肢とその理由を含める**
- 受容した妥協・仮実装は技術負債台帳へ
- 恒久層コンテキストに反映すべき規約・用語の変更

`context/` への書き込みは PR 経由で行います。エージェントが直接コミットする経路は設けません。

## AI レビューの扱い

AI によるレビューは**監査の入力**です。判定には使いません。承認(approve)もしません。独立レビュー(G-6)の代替にはなりません。

## 参照

- [ピットイン方式 標準本文](https://takenori-kusaka.github.io/process-compass/phase4-process-design/overview/) 
- [附属書E 開発者ガイド](https://takenori-kusaka.github.io/process-compass/phase4-process-design/developer-guide/)
- [附属書B EARS 記法](https://takenori-kusaka.github.io/process-compass/phase4-process-design/ears-guide/)     

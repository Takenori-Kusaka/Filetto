# PL-0002: ロール定義の乖離を検出する

対象 Issue: [#43](https://github.com/Takenori-Kusaka/Filetto/issues/43)
作成: 2026-08-13 / レーン: Platform

## 1. 何を作ったか

`.claude/skills/{role}/SKILL.md`(正本)と、各ランタイム向け生成物の乖離を検出する検査です。

| ファイル | 役割 |
| --- | --- |
| `scripts/gate/session-definition-drift.mjs` | 検査の本体 |
| `scripts/gate/session-definition-map.json` | 対応と、許容する差分。**運用に依存する値を検査の定数にしません**(`context/standards/extensibility.md`) |
| `tests/gate/test_session_definition_drift.py` | 検査そのものの検証。否定側6件を含む |
| `.github/workflows/gate-g5.yml` | `session-definition-drift` ジョブを追加し、集約の `needs` へ入れた |

**依頼2(生成経路)は作っていません。** PO 判断により、`.claude/skills/` の最適化期間が終わるまで後回しです。

## 2. 検査で実際に見つかった乖離

**検査を入れた時点で、既に2種類の乖離が積んでいました。**

| # | 内容 | 性質 |
| --- | --- | --- |
| 1 | `state:needs-platform` の欄。正本は「(**ラベル未作成**)」を含み、生成物は含まない | 生成物が古い |
| 2 | **タスクの粒度の記述2段落。** 行数の算定対象と除外、上限400行が暫定であること | **正本が新しく、生成物へ伝わっていない** |

**2 は #43 が予期したとおりの積み方です。** `CLAUDE.md` の「タスクの粒度」が更新され、正本の `SKILL.md` には反映されましたが、`.gemini/commands/dev.toml` には伝わっていませんでした。**Gemini CLI で動く Dev は、行数上限の適用範囲と除外を知らないまま作業することになります。**

本 PR で生成物を正本へ合わせ、乖離0件にしています。

## 3. 許容する差分の書き方

**ランタイム差は「事実として異なる記述」です。** 同じ文を配ると、事実と異なる記述が配られます。

`session-definition-map.json` の `allowedDifferences` に、**正本側の文・生成物側の文・理由**の3つを書きます。

```json
{
  "reason": "gh pr merge / gh pr review は Claude Code では設定で拒否されるが、Gemini CLI では拒否されない",
  "source": "- **`gh pr merge` と `gh pr review` はエージェントに拒否されます。** マージは人の操作",
  "generated": "- **`gh pr merge` と `gh pr review` を実行しません。** マージは人の操作です"
}
```

現在の許容差分は2件です。

| # | 箇所 | 理由 |
| --- | --- | --- |
| 1 | 禁止事項3の遮断 | `.claude/settings.json` による遮断は Gemini CLI に適用されない。本ランタイムでは指示への遵守だけが歯止めになることを明記する |
| 2 | `gh pr merge` / `gh pr review` | Claude Code では拒否されるが、Gemini CLI では拒否されない |

**許容した差分は、実行のたびに理由とともに出力します。** 黙って通しません。

**生成物から許容差分の文言が消えると、検査は失敗します。** `map` が古くなったことの証拠として扱います(否定テストで確認)。

## 4. 出力

```
  許容: .claude/skills/dev/SKILL.md → .gemini/commands/dev.toml
    理由: ...
    正本  : ...
    生成物: ...
許容した差分: 2 件
未展開のロール定義: 5 件
  .claude/skills/po/SKILL.md
  .claude/skills/qm/SKILL.md
  .claude/skills/audit/SKILL.md
  .claude/skills/platform/SKILL.md
  .claude/agents/tech-advisor.md
::notice::session-definition-drift: 1 組を検査、0 組で乖離を検出
```

**未展開のロール定義は失敗させません。** 生成経路が未着手であることは既知の状態です。**ただし数え上げて出力します。** 0件でないことが見えないと、「1組を検査して合格」が全体の合格に見えます。

`roleDefinitions` に書いたファイルが消えた場合は失敗します。**ロールが増えたのに対応を書き忘れる経路を残しません。**

## 5. 検証

```
$ node scripts/gate/session-definition-drift.mjs   → 1 組を検査、0 組で乖離を検出 (exit 0)
$ pytest tests/gate                                → 12 passed
$ node scripts/gate/double-encoding-check.mjs      → 158 ファイル、0 件
$ node scripts/gate/spec-lint.mjs                  → 32 ファイル、0 件
```

否定側の検証(いずれも一時ディレクトリへ写して壊し、本物は書き換えていません):

| # | 壊し方 | 期待 | 結果 |
| --- | --- | --- | --- |
| 1 | 生成物の本文を書き換える | 落ちる | 落ちた |
| 2 | 正本に追記する | 落ちる | 落ちた |
| 3 | 生成物を消す | 落ちる | 落ちた |
| 4 | 許容差分の文言を実在しないものにする | 落ちる | 落ちた |
| 5 | `pairs` を空にする | 落ちる | 落ちた |
| 6 | ロール定義を1件消す | 落ちる | 落ちた |

**5 は「対象0件を実施したことにして通す」経路を塞ぐためのものです。** `secret-scan` が空の設定で通っていた事例があります。

## 6. PO へ差し戻す点

**正本 `.claude/skills/dev/SKILL.md:44` の「(**ラベル未作成**)」という記述は、事実と異なります。**

```
$ gh label list
state:needs-platform  Platform の受信箱。検査・リント・CI/CD の改修依頼
state:needs-audit     Audit の受信箱。統合監査・リリースカットの検証依頼
```

**両ラベルとも作成済みです。** 本 PR では**正本を書き換えず、生成物を正本へ合わせました**。ロール定義の内容は Platform の領域ではないためです。**同じ記述が `.claude/skills/platform/SKILL.md` にもあります。**

正本の修正は PO / 文脈オーナーの判断でお願いします。

## 7. 残っていること

| # | 内容 | 時期 |
| --- | --- | --- |
| 1 | **生成経路**(正本から `.gemini/commands/*.toml` を生成する) | `.claude/skills/` の最適化期間の終了後(PO 判断) |
| 2 | PO / QM / Audit / Platform / tech-advisor の `.gemini` 展開 | 1 と同時。個別移植は二重管理を5倍にする |
| 3 | **Gemini CLI で禁止事項3(テスト側の変更による解消)を遮断できるか**の調査 | 未着手。不可能な場合は D-0 へ記録し、使用範囲を PO / Owner が判断する |

**3 は #43 の併せ依頼です。** 本 PR の範囲(依頼3' の検出)には含めていません。

## 8. 参照

- [#43](https://github.com/Takenori-Kusaka/Filetto/issues/43) — 本件の依頼と、範囲縮小の PO 判断
- [#27](https://github.com/Takenori-Kusaka/Filetto/issues/27) — 二重エンコード破損
- [PR #42](https://github.com/Takenori-Kusaka/Filetto/pull/42) — 破損版が `.gemini` へ移植されていたことの発見
- [PR #76](https://github.com/Takenori-Kusaka/Filetto/pull/76) — `docs/session-definitions/` の削除。正本が `.claude/` の1箇所になった
- `context/standards/extensibility.md` — 運用に依存する値を定数にしない

# S0 探索用コーパス

S0-001〜S0-004 で共通して使った 50 ファイルのコーパス本体です。Issue #20 の是正作業で、セッション専用の一時領域(scratchpad)から復元してリポジトリへ固定しました。

## 構成

| 接頭辞 | 推定される発行元 | 件数の目安 |
| --- | --- | --- |
| `kaminokawa-*` / `scan-kaminokawa-*` | 自治体の入札公告関連文書(南河内町とみられる) | PDF 7件(うち `scan-` 1件はスキャン相当に加工) |
| `kochi-*` / `scan-kochi-*` | 自治体の入札公告関連文書(高知県とみられる) | PDF/docx/xlsx 13件(うち `scan-` 1件はスキャン相当に加工) |
| `inashiki-*` | 自治体文書(稲敷市とみられる) | xls/doc/docx 10件 |
| `kakei-*` / `fig-kakei-*` | 家計調査関連資料(総務省統計局とみられる) | pdf/xlsx/png 6件 |
| `digital-*` / `fig-digital-*` | デジタル関連の公開資料 | pdf/png 6件 |
| `mhlw-*` | 厚生労働省関連資料とみられる | pptx 2件 |
| `chisou-01.pptx` | 出典未確認 | 1件 |
| `memo-ja-*` / `doc-en-01.md` | 検証用に作成したメモ(非公開文書由来ではない) | md 4件 |

**出典URLは記録が残っていません。** 上表の発行元は S0-001〜S0-004 のレポート記述とファイル名からの推定です。正確な出典URL・入手日は追跡できていないため、必要であれば別途追記してください(本READMEでは URL を断定的に記載しません)。

## 加工について

`scan-kaminokawa-03.pdf` と `scan-kochi-04.pdf` は、同名の原本(`kaminokawa-03.pdf` / `kochi-04.pdf`)をスキャン相当(画像化・劣化)に加工したものです。S0-002〜S0-004 の「スキャンPDF」検証で使用しました。

## 関連

- Issue #20 / Issue #12
- `docs/spikes/S0-001-graphify.md` 〜 `docs/spikes/S0-004-rag-fitness.md`
- `docs/spikes/assets/s0-004/` — S0-004 の評価スクリプト・クエリ定義

# S0-004 再現用アーティファクト

`docs/spikes/S0-004-rag-fitness.md` の「再現手順」が参照するスクリプト・評価セットです。Issue #20 の是正作業で、セッション専用の一時領域(scratchpad)から復元してリポジトリへ固定しました。

## 内容

| ファイル | 役割 |
| --- | --- |
| `rag-queries.json` | 受入基準1で「測定前に確定し、以後変更していない」とされる15問の評価セット |
| `kami-queries.json` | 神エクセル(kochi-14.xlsx / kakei-06.xlsx)向けの評価セット(S0-003 から継続使用) |
| `scan_routes.py` | スキャンPDF・画像の複数経路比較(pure/docling/rapidocr/easyocr-full/vlm/markitdown) |
| `exstruct_run.py` | .xlsx を ExStruct(`--mode light`)で処理し、行単位テキストへ線形化する |
| `rag_eval.py` | 抽出テキストを `<context>` として渡し、正答/誤答/回答不能を判定する |

## 実行に必要な追加ファイル

- コーパス本体: `../corpus/`
- `rag_eval.py` の評価には API 経由の LLM(S0-004 実行時は `claude-sonnet-4-6`)を使用します。評価専用で、推奨構成そのものには含まれません

## 未復元のもの

以下は Issue #20 の受入基準に含まれていないため、本コミットでは復元していません。

- S0-001/S0-002 のスクリプト(`inventory.py` / `baseline.py` 等)・Graphify検証用 venv
- S0-003 の中間生成物(`docling-parse.json` / `pure-parse.json` 等)・ExStruct検証用 venv
- 各経路の実行結果 JSON(`results-rag-*.json` / `route-*.json` 等)・中間テキスト群(`mix-*-text/` 等)

必要になった場合は、同じ scratchpad から個別に復元してください(未クリーンアップの場合のみ利用可能)。

## 関連

- Issue #20 / Issue #12
- `docs/spikes/S0-004-rag-fitness.md`
- `docs/spikes/assets/corpus/` — コーパス本体

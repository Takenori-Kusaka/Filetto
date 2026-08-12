# S0-004 検証1: RAG 適合性の判定。
# 抽出テキストのみを文脈として LLM に渡し、正答 / 誤答 / 回答不能 の3値で判定する。
# LLM は評価のためだけに使う(製品の構成要素ではない)。
import argparse
import json
import pathlib
import time

import anthropic

BASE = pathlib.Path(__file__).parent
SPEC = json.loads((BASE / "rag-queries.json").read_text(encoding="utf-8"))

ap = argparse.ArgumentParser()
ap.add_argument("--text-dir", required=True)
ap.add_argument("--tag", required=True)
ap.add_argument("--max-chars", type=int, default=12000)
args = ap.parse_args()

TEXT = BASE / args.text_dir

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

ANSWER_SYS = (
    "あなたは文書検索システムの一部です。与えられた<context>だけを根拠に、日本語で簡潔に答えてください。"
    "<context>に答えが含まれていない、または判読できない場合は、推測せず必ず「情報がない」とだけ答えてください。"
    "一般常識や事前知識で補ってはいけません。"
)

JUDGE_SYS = (
    "あなたは採点者です。question に対する correct_answer と "
    "model_answer を比較し、次の3値のいずれかだけを出力してください。\n"
    "正答: model_answer が correct_answer と実質的に同じ内容を述べている\n"
    "誤答: model_answer が correct_answer と異なる内容を述べている(数値違い・対象違いを含む)\n"
    "回答不能: model_answer が「情報がない」等、答えられないと述べている\n"
    "出力は 正答 / 誤答 / 回答不能 のいずれか1語のみ。"
)


def ask(system, user, max_tokens=400):
    for attempt in range(3):
        try:
            r = client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                       messages=[{"role": "user", "content": user}])
            return r.content[0].text.strip(), r.usage.input_tokens, r.usage.output_tokens
        except Exception as e:
            if attempt == 2:
                return f"<ERROR {e}>", 0, 0
            time.sleep(3)


rows = []
tin = tout = 0
counts = {"正答": 0, "誤答": 0, "回答不能": 0, "その他": 0}

for q in SPEC["questions"]:
    p = TEXT / (q["doc"] + ".txt")
    ctx = p.read_text(encoding="utf-8") if p.exists() else ""
    ctx = ctx[: args.max_chars]
    if not ctx.strip():
        verdict, ans = "回答不能", "<抽出テキストが空>"
        counts[verdict] += 1
        rows.append({**q, "context_chars": 0, "model_answer": ans, "verdict": verdict})
        print(f"{q['id']:<4} {q['kind']:<8} ctx=0      {verdict}  (抽出テキストが空)")
        continue

    ans, i1, o1 = ask(ANSWER_SYS, f"<context>\n{ctx}\n</context>\n\n質問: {q['q']}")
    v, i2, o2 = ask(JUDGE_SYS,
                    json.dumps({"question": q["q"], "correct_answer": q["a"], "model_answer": ans},
                               ensure_ascii=False), 20)
    tin += i1 + i2
    tout += o1 + o2
    verdict = v if v in counts else "その他"
    counts[verdict] += 1
    rows.append({**q, "context_chars": len(ctx), "model_answer": ans, "verdict": verdict})
    print(f"{q['id']:<4} {q['kind']:<8} ctx={len(ctx):<6} {verdict:<6} {ans[:70]}")

print(f"\n=== {args.tag} ===")
print(
    f"正答 {counts['正答']} / 誤答 {counts['誤答']} / "
    f"回答不能 {counts['回答不能']} / その他 {counts['その他']}  "
    f"(全 {len(SPEC['questions'])} 問)"
)
print(f"評価に使ったトークン: {tin} in / {tout} out")
(BASE / f"results-rag-{args.tag}.json").write_text(
    json.dumps({"tag": args.tag, "text_dir": args.text_dir, "model": MODEL,
                "counts": counts, "tokens": {"in": tin, "out": tout}, "rows": rows},
               ensure_ascii=False, indent=1), encoding="utf-8")

"""S0-006 基準5 の代替測定: 正解文字列が抽出テキストに残っているかを機械的に数える。

S0-004 は LLM を判定に使った。本測定は LLM を使わず、
「正解に到達するために必要な文字列が抽出テキストに存在するか」だけを見る。
これは RAG 適合性の下限であって、LLM 判定の代替ではない。
存在しなければ確実に答えられない。存在しても答えられるとは限らない。

OCR の差し替えが影響するのは R01〜R08(スキャンPDF2件 + 図表画像4件)のみ。
R09〜R15 は .xlsx / .docx / 通常PDF であり、本変更の影響を受けない。
"""
import json
import re
import unicodedata
from pathlib import Path

DEV = Path(
    r"C:\Users\kokor\AppData\Local\Temp\claude\E--Github-Filetto-dev"
    r"\2504b730-c661-4318-ad58-32bb65612f92\scratchpad"
)
HERE = Path(__file__).parent

# S0-004 の rag-queries.json と同じ正解。
# needles は「正解に到達するために抽出テキストへ現れる必要がある文字列」。
# いずれか1つでも欠ければ、その問いは文脈だけでは答えられない。
CASES = [
    ("R01", "scan-kaminokawa-03.pdf", ["契約書", "7日"]),
    ("R02", "scan-kaminokawa-03.pdf", ["契約保証", "500万円"]),
    ("R03", "scan-kaminokawa-03.pdf", ["工程表", "100万円"]),
    ("R04", "scan-kochi-04.pdf", ["高知県外"]),
    ("R05", "fig-digital-01.png", ["2025年", "3月までに普及", "おおむね全ての医療機関"]),
    ("R06", "fig-digital-02.png", ["データ", "取扱", "ルール"]),
    ("R08b", "fig-kakei-02.png", ["最近の動向"]),
    ("R07", "fig-kakei-01.png", ["単純平均"]),
    ("R08", "fig-kakei-02.png", ["家計調査"]),
]

ROUTES = {
    "rapidocr-v6(S0-004 推奨)": DEV / "route-rapidocr-text",
    "rapidocr-ja(PP-OCRv4)": HERE / "route-rapidocr-ja4-text",
    "rapidocr-v6 + 字形正規化": None,  # v6 の出力へ正規化を当てたもの
    "vlm": DEV / "route-vlm-text",
    "easyocr-full": DEV / "route-easyocr-full-text",
}

TABLE = {"带": "帯", "查": "査", "笺": "箋", "项": "項", "閱": "閲"}


def norm(t: str) -> str:
    """全角半角・空白の揺れを吸収する。OCR は語中に空白を入れることがある。"""
    t = unicodedata.normalize("NFKC", t)
    return re.sub(r"\s+", "", t)


def load(d: Path, name: str, fix: bool) -> str:
    p = d / f"{name}.txt"
    if not p.exists():
        return ""
    t = p.read_text(encoding="utf-8", errors="replace")
    if fix:
        t = "".join(TABLE.get(c, c) for c in t)
    return norm(t)


def main():
    out = {}
    for label in ROUTES:
        fix = "正規化" in label
        d = ROUTES[label] or DEV / "route-rapidocr-text"
        rows = []
        for qid, fname, needles in CASES:
            text = load(d, fname, fix)
            miss = [n for n in needles if norm(n) not in text]
            rows.append({"q": qid, "file": fname, "missing": miss, "ok": not miss})
        out[label] = {
            "hit": sum(r["ok"] for r in rows),
            "total": len(rows),
            "rows": rows,
        }

    Path("answer-presence.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{'経路':<28}{'到達可能':>9}  欠落した問い")
    for label, r in out.items():
        miss = [
            f"{x['q']}({'/'.join(x['missing'])})" for x in r["rows"] if not x["ok"]
        ]
        print(f"{label:<28}{r['hit']}/{r['total']:>7}  {' '.join(miss) or '-'}")


if __name__ == "__main__":
    main()

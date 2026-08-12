"""S0-006 基準1 / 基準3: 日本語文書に出現しない字形の混入を数える。

判定方法:
  CJK 統合漢字(および拡張A)のうち、CP932(JIS X 0208 + NEC/IBM 拡張)へ
  エンコードできない文字を「日本語の文書組版に出現しない字形」とみなす。
  CP932 は日本語 Windows の標準文字集合であり、簡体字・中国語専用字形は
  ここに含まれない。判定は決定的で、辞書の版に依存しない。

  補集合として EUC-JP でも同じ判定を行い、両者が一致することを確認する。
"""
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

DEV = Path(
    r"C:\Users\kokor\AppData\Local\Temp\claude\E--Github-Filetto-dev"
    r"\2504b730-c661-4318-ad58-32bb65612f92\scratchpad"
)

# 測定対象の経路。route-* はスキャンPDF2件+図表画像4件のみを含む
ROUTES = {
    "rapidocr": DEV / "route-rapidocr-text",
    "easyocr-full": DEV / "route-easyocr-full-text",
    "vlm": DEV / "route-vlm-text",
}
# 対照: 原本のテキスト層のみを使う経路(OCR を通さない)
CONTROL = DEV / "pure-text"


def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF      # CJK 統合漢字
        or 0x3400 <= cp <= 0x4DBF   # 拡張A
        or 0xF900 <= cp <= 0xFAFF   # 互換漢字
        or 0x20000 <= cp <= 0x2FA1F  # 拡張B以降
    )


def encodable(ch: str, enc: str) -> bool:
    try:
        ch.encode(enc)
        return True
    except UnicodeEncodeError:
        return False


def audit_text(text: str):
    total = len(text)
    cjk = [c for c in text if is_cjk(c)]
    bad_cp932 = [c for c in cjk if not encodable(c, "cp932")]
    bad_eucjp = [c for c in cjk if not encodable(c, "euc_jp")]
    return {
        "chars": total,
        "cjk": len(cjk),
        "hits_cp932": len(bad_cp932),
        "hits_eucjp": len(bad_eucjp),
        "rate_pct": round(100 * len(bad_cp932) / total, 4) if total else 0.0,
        "counter": Counter(bad_cp932),
    }


def audit_dir(d: Path):
    per_file = {}
    agg = Counter()
    tot_chars = tot_hits = tot_cjk = 0
    disagree = 0
    for f in sorted(d.glob("*.txt")):
        r = audit_text(f.read_text(encoding="utf-8", errors="replace"))
        agg += r["counter"]
        tot_chars += r["chars"]
        tot_hits += r["hits_cp932"]
        tot_cjk += r["cjk"]
        disagree += abs(r["hits_cp932"] - r["hits_eucjp"])
        per_file[f.name.replace(".txt", "")] = {
            "chars": r["chars"],
            "cjk": r["cjk"],
            "hits": r["hits_cp932"],
            "rate_pct": r["rate_pct"],
            "glyphs": dict(r["counter"].most_common()),
        }
    return {
        "total_chars": tot_chars,
        "total_cjk": tot_cjk,
        "total_hits": tot_hits,
        "rate_pct": round(100 * tot_hits / tot_chars, 4) if tot_chars else 0.0,
        "cp932_vs_eucjp_disagreement": disagree,
        "glyphs": dict(agg.most_common()),
        "per_file": per_file,
    }


def main():
    out = {"method": "CJK ideograph not encodable in CP932", "routes": {}}
    for name, d in ROUTES.items():
        if not d.exists():
            print(f"MISSING: {d}", file=sys.stderr)
            continue
        out["routes"][name] = audit_dir(d)
    if CONTROL.exists():
        out["control_pure_text"] = audit_dir(CONTROL)

    Path("glyph-audit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{'経路':<16}{'文字数':>9}{'漢字':>8}{'混入':>7}{'混入率%':>9}  不一致")
    for name, r in out["routes"].items():
        print(
            f"{name:<16}{r['total_chars']:>9}{r['total_cjk']:>8}"
            f"{r['total_hits']:>7}{r['rate_pct']:>9}  {r['cp932_vs_eucjp_disagreement']}"
        )
    if "control_pure_text" in out:
        r = out["control_pure_text"]
        print(
            f"{'(対照)pure':<16}{r['total_chars']:>9}{r['total_cjk']:>8}"
            f"{r['total_hits']:>7}{r['rate_pct']:>9}  {r['cp932_vs_eucjp_disagreement']}"
        )

    for name, r in out["routes"].items():
        if not r["glyphs"]:
            continue
        print(f"\n[{name}] 混入した字形(上位20)")
        for ch, n in list(r["glyphs"].items())[:20]:
            try:
                nm = unicodedata.name(ch)
            except ValueError:
                nm = "?"
            print(f"  {ch}  U+{ord(ch):04X}  {n:>3}回  {nm}")


if __name__ == "__main__":
    main()

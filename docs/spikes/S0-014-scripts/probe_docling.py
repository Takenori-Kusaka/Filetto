"""S0-014 経路2・3: Docling の出力が位置(ページ番号・段落/スライドの通し番号・領域の座標)を
含むかを測る。

判定は行わない。取れた値を貼るための出力を作る。
"""

import json
import sys
import time
from pathlib import Path

from docling.document_converter import DocumentConverter

CORPUS = Path(sys.argv[1])
OUT = {}

conv = DocumentConverter()

for name in sys.argv[2:]:
    src = CORPUS / name
    t0 = time.time()
    try:
        res = conv.convert(str(src))
    except Exception as e:  # noqa: BLE001
        OUT[name] = {"error": f"{type(e).__name__}: {e}"}
        continue
    elapsed = round(time.time() - t0, 2)

    doc = res.document
    d = doc.export_to_dict()

    items = []
    with_prov = 0
    total = 0
    pages_seen = set()
    for key in ("texts", "tables", "pictures"):
        for it in d.get(key, []):
            total += 1
            prov = it.get("prov") or []
            if prov:
                with_prov += 1
                for p in prov:
                    if "page_no" in p:
                        pages_seen.add(p["page_no"])
            if len(items) < 6 and prov:
                items.append(
                    {
                        "kind": key,
                        "self_ref": it.get("self_ref"),
                        "label": it.get("label"),
                        "prov": prov[:1],
                        "text_head": (it.get("text") or "")[:40],
                    }
                )

    OUT[name] = {
        "elapsed_sec": elapsed,
        "num_pages": len(d.get("pages", {})) or len(pages_seen),
        "page_numbers_seen": sorted(pages_seen)[:20],
        "items_total": total,
        "items_with_prov": with_prov,
        "sample_items": items,
        "top_level_keys": sorted(d.keys()),
    }

Path("s0014-docling.json").write_text(
    json.dumps(OUT, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("wrote s0014-docling.json")

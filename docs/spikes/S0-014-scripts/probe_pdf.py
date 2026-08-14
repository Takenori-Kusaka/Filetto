"""S0-014 経路3: Docling + RapidOCR(force_full_page_ocr)の出力が
ページ番号と領域の座標を含むかを測る。
"""

import json
import sys
import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption

opts = PdfPipelineOptions()
opts.do_ocr = True
opts.ocr_options = RapidOcrOptions(force_full_page_ocr=True)

conv = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=opts),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=opts),
    }
)

CORPUS = Path(sys.argv[1])
OUT = {}

for name in sys.argv[2:]:
    src = CORPUS / name
    t0 = time.time()
    try:
        res = conv.convert(str(src))
    except Exception as e:  # noqa: BLE001
        OUT[name] = {"error": f"{type(e).__name__}: {e}"}
        continue
    elapsed = round(time.time() - t0, 2)
    d = res.document.export_to_dict()

    total = with_prov = 0
    pages = set()
    samples = []
    for key in ("texts", "tables", "pictures"):
        for it in d.get(key, []):
            total += 1
            prov = it.get("prov") or []
            if prov:
                with_prov += 1
                for p in prov:
                    if "page_no" in p:
                        pages.add(p["page_no"])
                if len(samples) < 4:
                    samples.append(
                        {
                            "kind": key,
                            "self_ref": it.get("self_ref"),
                            "label": it.get("label"),
                            "prov": prov[:1],
                            "text_head": (it.get("text") or "")[:36],
                        }
                    )

    OUT[name] = {
        "elapsed_sec": elapsed,
        "declared_pages": sorted(int(k) for k in d.get("pages", {}).keys()),
        "page_numbers_in_prov": sorted(pages),
        "items_total": total,
        "items_with_prov": with_prov,
        "sample_items": samples,
    }
    print(name, "done", elapsed, "s", flush=True)

Path("s0014-pdf.json").write_text(
    json.dumps(OUT, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("wrote s0014-pdf.json")

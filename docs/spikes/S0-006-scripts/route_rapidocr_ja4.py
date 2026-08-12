"""S0-006 基準2: RapidOCR の認識モデルを日本語向け(LangRec.JAPAN)へ差し替えて測る。

S0-004 の scan_routes.py --route rapidocr と同一のコーパス・同一の対象6件。
差分は Rec.lang_type を japan にする1点のみ。
"""
import json
import pathlib
import time

DEV = pathlib.Path(
    r"C:\Users\kokor\AppData\Local\Temp\claude\E--Github-Filetto-dev"
    r"\2504b730-c661-4318-ad58-32bb65612f92\scratchpad"
)
CORPUS = DEV / "corpus"
TARGETS = [
    "scan-kaminokawa-03.pdf",
    "scan-kochi-04.pdf",
    "fig-digital-01.png",
    "fig-digital-02.png",
    "fig-kakei-01.png",
    "fig-kakei-02.png",
]
OUT = pathlib.Path(__file__).parent / "route-rapidocr-ja4-text"
OUT.mkdir(exist_ok=True)


def main():
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from rapidocr import LangRec, ModelType, OCRVersion

    o = PdfPipelineOptions()
    o.do_ocr = True
    o.ocr_options = RapidOcrOptions(
        force_full_page_ocr=True,
        rapidocr_params={
            "Rec.lang_type": LangRec.JAPAN,
            "Rec.ocr_version": OCRVersion.PPOCRV4,
            "Rec.model_type": ModelType.MOBILE,
        },
    )
    conv = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=o),
            InputFormat.IMAGE: PdfFormatOption(pipeline_options=o),
        }
    )
    rows = []
    for name in TARGETS:
        t0 = time.time()
        try:
            txt = conv.convert(str(CORPUS / name)).document.export_to_markdown()
            err = ""
        except Exception as e:  # noqa: BLE001
            txt, err = "", repr(e)[:300]
        dt = time.time() - t0
        (OUT / f"{name}.txt").write_text(txt, encoding="utf-8")
        rows.append({"file": name, "chars": len(txt), "sec": round(dt, 1), "err": err})
        print(f"{name:<28} {len(txt):>6}字 {dt:>7.1f}s {err}", flush=True)

    total = sum(r["sec"] for r in rows)
    print(f"合計 {total:.1f}s")
    pathlib.Path("route-rapidocr-ja4.json").write_text(
        json.dumps({"rows": rows, "total_sec": round(total, 1)},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

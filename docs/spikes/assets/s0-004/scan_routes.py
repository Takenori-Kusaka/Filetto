# S0-004 検証2: スキャン PDF と図表画像の内容取得を複数経路で比較する(いずれもローカル完結)
import pathlib, time, json, sys, argparse, re

BASE = pathlib.Path(__file__).parent
CORPUS = BASE / "corpus"
TARGETS = ["scan-kaminokawa-03.pdf", "scan-kochi-04.pdf",
           "fig-digital-01.png", "fig-digital-02.png", "fig-kakei-01.png", "fig-kakei-02.png"]

ap = argparse.ArgumentParser()
ap.add_argument("--route", required=True, choices=["vlm", "markitdown", "rapidocr", "easyocr-full"])
args = ap.parse_args()

OUT = BASE / f"route-{args.route}-text"
OUT.mkdir(exist_ok=True)
rows = []


def run_docling_vlm():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import VlmPipelineOptions
    from docling.pipeline.vlm_pipeline import VlmPipeline
    opts = VlmPipelineOptions()
    conv = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline, pipeline_options=opts),
        InputFormat.IMAGE: PdfFormatOption(pipeline_cls=VlmPipeline, pipeline_options=opts),
    })
    for name in TARGETS:
        t0 = time.time()
        try:
            r = conv.convert(str(CORPUS / name))
            txt = r.document.export_to_markdown()
            err = ""
        except Exception as e:
            txt, err = "", repr(e)[:200]
        yield name, txt, time.time() - t0, err


def run_markitdown():
    from markitdown import MarkItDown
    md = MarkItDown(enable_plugins=False)
    for name in TARGETS:
        t0 = time.time()
        try:
            txt = md.convert(str(CORPUS / name)).text_content
            err = ""
        except Exception as e:
            txt, err = "", repr(e)[:200]
        yield name, txt, time.time() - t0, err


def run_rapidocr():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    o = PdfPipelineOptions()
    o.do_ocr = True
    o.ocr_options = RapidOcrOptions(force_full_page_ocr=True)
    conv = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=o),
        InputFormat.IMAGE: PdfFormatOption(pipeline_options=o),
    })
    for name in TARGETS:
        t0 = time.time()
        try:
            txt = conv.convert(str(CORPUS / name)).document.export_to_markdown()
            err = ""
        except Exception as e:
            txt, err = "", repr(e)[:200]
        yield name, txt, time.time() - t0, err


def run_easyocr_full():
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
    o = PdfPipelineOptions()
    o.do_ocr = True
    o.ocr_options = EasyOcrOptions(lang=["ja", "en"], force_full_page_ocr=True)
    conv = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=o),
        InputFormat.IMAGE: PdfFormatOption(pipeline_options=o),
    })
    for name in TARGETS:
        t0 = time.time()
        try:
            txt = conv.convert(str(CORPUS / name)).document.export_to_markdown()
            err = ""
        except Exception as e:
            txt, err = "", repr(e)[:200]
        yield name, txt, time.time() - t0, err


gen = {"vlm": run_docling_vlm, "markitdown": run_markitdown, "rapidocr": run_rapidocr,
       "easyocr-full": run_easyocr_full}[args.route]()

total = 0.0
for name, txt, sec, err in gen:
    norm = re.sub(r"\s+", " ", txt).strip()
    (OUT / (name + ".txt")).write_text(norm, encoding="utf-8")
    total += sec
    jp = len(re.findall(r"[぀-ヿ一-鿿]", norm))
    rows.append({"file": name, "chars": len(norm), "jp_chars": jp, "sec": round(sec, 1), "error": err})
    print(f"{name:<26} {len(norm):>7} chars (日本語 {jp:>6}) {sec:>7.1f}s {err}", flush=True)

print(f"TOTAL {total:.1f}s")
(BASE / f"route-{args.route}.json").write_text(
    json.dumps({"route": args.route, "total_sec": total, "rows": rows}, ensure_ascii=False, indent=1),
    encoding="utf-8")

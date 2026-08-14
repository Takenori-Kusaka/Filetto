"""S0-014 経路4・5: xlrd(.xls) と olefile(.doc) が位置に相当する情報を返すかを測る。

出力は「取れた値そのもの」を貼るためのもの。判定は行わない。
"""

import json
import sys
from pathlib import Path

CORPUS = Path(sys.argv[1])
OUT = {}


def probe_xlrd(path: Path) -> dict:
    import xlrd

    book = xlrd.open_workbook(str(path))
    sheets = []
    for si in range(book.nsheets):
        sh = book.sheet_by_index(si)
        cells = []
        for r in range(min(sh.nrows, 2000)):
            for c in range(sh.ncols):
                v = sh.cell_value(r, c)
                if isinstance(v, str) and v.strip():
                    cells.append({"sheet": sh.name, "row": r, "col": c, "text": v.strip()})
        sheets.append(
            {"name": sh.name, "nrows": sh.nrows, "ncols": sh.ncols, "text_cells": len(cells)}
        )
    first = cells[:5] if cells else []
    return {
        "library": "xlrd",
        "version": xlrd.__version__,
        "sheets": sheets,
        "sample_cells": first,
    }


def probe_olefile(path: Path) -> dict:
    import olefile

    ole = olefile.OleFileIO(str(path))
    streams = ["/".join(s) for s in ole.listdir()]
    # WordDocument ストリームの本文を取り出す経路が存在するかを見る
    has_worddoc = "WordDocument" in streams
    sizes = {s: ole.get_size(s) for s in streams}
    ole.close()
    return {
        "library": "olefile",
        "version": olefile.__version__,
        "streams": streams,
        "stream_sizes": sizes,
        "has_WordDocument_stream": has_worddoc,
        "paragraph_index_available": False,
        "note": "olefile は OLE 複合ドキュメントのストリームを列挙・読み出すライブラリ。"
        "段落・ページ・文字位置を表す API は存在しない",
    }


for name in sys.argv[2:]:
    p = CORPUS / name
    try:
        if p.suffix.lower() == ".xls":
            OUT[name] = probe_xlrd(p)
        else:
            OUT[name] = probe_olefile(p)
    except Exception as e:  # noqa: BLE001
        OUT[name] = {"error": f"{type(e).__name__}: {e}"}

print(json.dumps(OUT, ensure_ascii=False, indent=2))

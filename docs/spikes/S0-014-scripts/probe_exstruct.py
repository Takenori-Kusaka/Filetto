"""S0-014 経路1: ExStruct light が、線形化の前にシート名とセル座標を返すかを測る。

exstruct CLI の JSON 出力から、位置に相当する欄だけを取り出して数える。
"""

import json
import subprocess
import sys
import time
from pathlib import Path

EXSTRUCT = sys.argv[1]
CORPUS = Path(sys.argv[2])
OUT = {}

for name in sys.argv[3:]:
    src = CORPUS / name
    dst = Path(f"{src.stem}.exstruct.json")
    t0 = time.time()
    proc = subprocess.run(
        [EXSTRUCT, "-m", "light", "--pretty", "-o", str(dst), str(src)],
        capture_output=True,
        text=True,
    )
    elapsed = round(time.time() - t0, 2)
    if proc.returncode != 0:
        OUT[name] = {"error": proc.stderr.strip()[:400], "returncode": proc.returncode}
        continue

    data = json.loads(dst.read_text(encoding="utf-8"))
    sheets = data.get("sheets", {})
    per_sheet = {}
    samples = []
    for sheet_name, sheet in sheets.items():
        rows = sheet.get("rows", [])
        cells = 0
        for row in rows:
            r = row.get("r")
            for col, text in row.get("c", {}).items():
                cells += 1
                if len(samples) < 5 and isinstance(text, str) and text.strip():
                    samples.append(
                        {"sheet": sheet_name, "r": r, "c": int(col), "text": text.strip()[:40]}
                    )
        per_sheet[sheet_name] = {"rows_with_values": len(rows), "cells_with_values": cells}

    OUT[name] = {
        "elapsed_sec": elapsed,
        "top_level_keys": sorted(data.keys()),
        "sheet_count": len(sheets),
        "sheet_keys": sorted(sheets.keys()),
        "row_object_keys": sorted(next(iter(sheets.values()))["rows"][0].keys())
        if sheets
        else [],
        "per_sheet": per_sheet,
        "sample_cells_with_coordinates": samples,
        "output_bytes": dst.stat().st_size,
    }

Path("s0014-exstruct.json").write_text(
    json.dumps(OUT, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("wrote s0014-exstruct.json")

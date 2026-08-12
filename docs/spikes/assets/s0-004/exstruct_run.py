# ExStruct の JSON を行単位のテキストへ線形化する(検証3の第3条件)
import json, pathlib, subprocess, time, sys

BASE = pathlib.Path(__file__).parent
EXE = BASE / "exenv/Scripts/exstruct.exe"
OUT = BASE / "exstruct-text"
OUT.mkdir(exist_ok=True)

TARGETS = ["kochi-14.xlsx", "kakei-06.xlsx", "kochi-03.xlsx", "inashiki-01.xls"]

for fn in TARGETS:
    src = BASE / "corpus" / fn
    js = BASE / f"ex-{src.stem}.json"
    t0 = time.time()
    p = subprocess.run([str(EXE), str(src), "--mode", "light", "--alpha-col",
                        "-o", str(js), "--pretty"], capture_output=True, timeout=600)
    sec = time.time() - t0
    if p.returncode != 0 or not js.exists():
        print(f"{fn:<20} FAILED rc={p.returncode} {p.stderr.decode('utf-8','ignore')[-200:]}")
        continue
    d = json.loads(js.read_text(encoding="utf-8"))
    lines = [f"# {d.get('book_name')}"]
    for sheet, sd in d.get("sheets", {}).items():
        lines.append(f"## sheet: {sheet}")
        for row in sd.get("rows", []):
            cells = sd and row.get("c", {})
            vals = [f"{k}={str(v).strip()}" for k, v in cells.items() if str(v).strip()]
            if vals:
                lines.append(f"r{row.get('r')}: " + " | ".join(vals))
        for sh in sd.get("shapes", []) or []:
            t = (sh.get("text") or "").strip()
            if t:
                lines.append(f"shape: {t}")
    text = "\n".join(lines)
    (OUT / (fn + ".txt")).write_text(text, encoding="utf-8")
    print(f"{fn:<20} ok {len(text):>8} chars {sec:>6.1f}s  json={js.stat().st_size}")

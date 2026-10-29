"""オフライン Lore の .lore の中身と flush 後の複製可否を手元で確かめる"""

import hashlib
import shutil
import sys
import time
from pathlib import Path

from lore import Lore
from lore.types.args import (
    LoreFileHistoryArgs,
    LoreFileStageArgs,
    LoreFileWriteArgs,
    LoreGlobalArgs,
    LoreRepositoryCreateArgs,
    LoreRepositoryFlushArgs,
    LoreRevisionCommitArgs,
)
from lore.types.enums import LoreEventTag

root = Path(sys.argv[1]).resolve()
copy = Path(sys.argv[2]).resolve()
shutil.rmtree(root, ignore_errors=True)
shutil.rmtree(copy, ignore_errors=True)
root.mkdir(parents=True)
g = LoreGlobalArgs(repository_path=str(root), offline=True)
Lore.repository_create(g, LoreRepositoryCreateArgs(repository_url="filetto")).wait()


def tree(p):
    out = {}
    for f in sorted(Path(p).rglob("*")):
        if f.is_file():
            out[str(f.relative_to(p))] = (
                f.stat().st_size,
                hashlib.sha256(f.read_bytes()).hexdigest()[:8],
            )
    return out


def commit(path, content):
    t = root / path
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_bytes(content)
    Lore.file_stage(g, LoreFileStageArgs(paths=[str(t)])).wait()
    nums = []

    def cb(e, _):
        if LoreEventTag(e.tag).name == "REVISION_COMMIT_REVISION":
            nums.append(e.get_data().revision_number)

    Lore.revision_commit(g, LoreRevisionCommitArgs(message=path)).callback(cb).wait()
    return nums[0]


prev = tree(root / ".lore")
for i in range(1, 4):
    n = commit("a.txt", (f"version {i}\n" * 1000).encode())
    t0 = time.perf_counter()
    Lore.repository_flush(g, LoreRepositoryFlushArgs()).wait()
    tf = time.perf_counter() - t0
    now = tree(root / ".lore")
    changed = {k for k in now if now.get(k) != prev.get(k)}
    removed = set(prev) - set(now)
    print(
        f"commit #{n}: flush {tf * 1000:.0f}ms, .lore files={len(now)}"
        f" changed={len(changed)} removed={len(removed)}"
    )
    for k in sorted(changed):
        print("   +", k, now[k][0])
    for k in sorted(removed):
        print("   -", k)
    prev = now

print("\n.lore tree:")
[print("  ", k, v[0]) for k, v in prev.items()]

# 複製先で全版を読めるか(作業ファイルは写さず、.lore だけを写す)
copy.mkdir(parents=True)
shutil.copytree(root / ".lore", copy / ".lore")
(copy / "a.txt").write_bytes((root / "a.txt").read_bytes())
g2 = LoreGlobalArgs(repository_path=str(copy), offline=True)
nums = []


def hist(e, _):
    if LoreEventTag(e.tag).name == "FILE_HISTORY":
        nums.append(str(e.get_data().revision_number))


Lore.file_history(g2, LoreFileHistoryArgs(path=str(copy / "a.txt"))).callback(hist).wait()
print("\ncopy history:", nums)
for n in nums:
    out = copy / f"out-{n}"
    Lore.file_write(
        g2, LoreFileWriteArgs(path=str(copy / "a.txt"), revision=n, output=str(out))
    ).wait()
    print("  rev", n, "->", out.read_bytes()[:12])

"""案H のフィジビリティ検証: Lambda の /tmp 上のオフライン Lore + S3 の目録(manifest)の CAS。

op:
  info          実行環境(glibc・lore の版・冷えた起動か)
  save          path と content(base64)か gen_bytes(大きさ)で版を保存し、
                flush の後に差分を S3 へ写す
  versions      path の版の一覧
  read          path と version の内容(sha256・大きさ・先頭)
  reset         /tmp の保管を消す(冷えた起動の模擬)
  stale_push    古い ETag で目録を進めようとし、412 になることを確かめる
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.config import Config as _BotoConfig
from botocore.exceptions import ClientError

# Lore は起動時に $HOME/.config/lore を作る。Lambda では /tmp 以外が読み取り専用のため、
# lore を読み込む前に HOME を /tmp へ向ける
# (要件: 配置側で HOME か XDG_CONFIG_HOME を書ける場所にする)
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ["HOME"] = "/tmp/home"
    os.environ["XDG_CONFIG_HOME"] = "/tmp/home/.config"
    os.makedirs("/tmp/home/.config", exist_ok=True)

BUCKET = os.environ["BUCKET"]
PREFIX = os.environ.get("PREFIX", "lore/")
ROOT = Path(os.environ.get("REPO_ROOT", "/tmp/repo"))
MANIFEST_KEY = PREFIX + "manifest.json"
OBJECTS = PREFIX + "objects/"
PARALLEL = int(os.environ.get("PARALLEL", "16"))

s3 = boto3.client("s3", config=_BotoConfig(max_pool_connections=max(PARALLEL, 10)))

_COLD = True
_etag: str | None = None  # 最後に読んだ/書いた目録の ETag
_seq = 0
_local: dict[str, str] = {}  # 同期済みの rel -> sha


# ---------------------------------------------------------------- S3 の目録と CAS
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


LORE_ONLY = os.environ.get("SYNC_LORE_ONLY", "0") == "1"  # 作業ファイル(原本の写し)を S3 へ写さない


def _tree(root: Path) -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            rel = f.relative_to(root).as_posix()
            if LORE_ONLY and not rel.startswith(".lore/"):
                continue
            data = f.read_bytes()
            out[rel] = (_sha(data), len(data))
    return out


def _get_manifest() -> tuple[dict, str | None]:
    try:
        r = s3.get_object(Bucket=BUCKET, Key=MANIFEST_KEY)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return {"seq": 0, "files": {}}, None
        raise
    return json.load(r["Body"]), r["ETag"]


def pull() -> dict:
    """目録を読み、手元の保管を目録に合わせる。冷えた起動では全体を取り込む"""
    global _etag, _seq, _local
    t0 = time.perf_counter()
    m, etag = _get_manifest()
    if ROOT.exists() and etag == _etag and _local:
        return {"pull_ms": _ms(t0), "pulled": 0, "skipped": True, "seq": m["seq"]}
    ROOT.mkdir(parents=True, exist_ok=True)
    have = _tree(ROOT) if ROOT.exists() else {}
    todo = [
        (rel, meta) for rel, meta in m["files"].items() if have.get(rel, ("", 0))[0] != meta["sha"]
    ]

    def fetch(item):
        rel, meta = item
        body = s3.get_object(Bucket=BUCKET, Key=OBJECTS + meta["sha"])["Body"].read()
        if _sha(body) != meta["sha"]:
            raise RuntimeError(f"content hash mismatch for {rel}")
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        return len(body)

    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        sizes = list(pool.map(fetch, todo))
    pulled = len(sizes)
    pulled_bytes = sum(sizes)
    for rel in set(have) - set(m["files"]):
        (ROOT / rel).unlink()
    _etag, _seq = etag, m["seq"]
    _local = {rel: meta["sha"] for rel, meta in m["files"].items()}
    return {
        "pull_ms": _ms(t0),
        "pulled": pulled,
        "pulled_bytes": pulled_bytes,
        "skipped": False,
        "seq": m["seq"],
    }


def push(if_match: str | None = "__current__") -> dict:
    """flush 済みの保管の差分を内容のハッシュ名で置き、目録を If-Match で進める"""
    global _etag, _seq, _local
    t0 = time.perf_counter()
    cur = _tree(ROOT)
    changed = {rel: sha for rel, (sha, _) in cur.items() if _local.get(rel) != sha}
    by_sha = {sha: rel for rel, sha in changed.items()}

    def upload(sha: str) -> int:
        data = (ROOT / by_sha[sha]).read_bytes()
        try:
            s3.put_object(Bucket=BUCKET, Key=OBJECTS + sha, Body=data, IfNoneMatch="*")
            return len(data)
        except ClientError as e:
            if e.response["ResponseMetadata"]["HTTPStatusCode"] == 412:
                return -1  # 同じ内容が既にある
            raise

    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        results = list(pool.map(upload, sorted(by_sha)))
    uploaded = sum(1 for r in results if r >= 0)
    uploaded_bytes = sum(r for r in results if r >= 0)
    dedup = sum(1 for r in results if r < 0)
    manifest = {
        "seq": _seq + 1,
        "written_at": datetime.now(UTC).isoformat(),
        "files": {rel: {"sha": sha, "size": size} for rel, (sha, size) in cur.items()},
    }
    body = json.dumps(manifest, separators=(",", ":")).encode()
    expected = _etag if if_match == "__current__" else if_match
    kwargs = {"IfMatch": expected} if expected else {"IfNoneMatch": "*"}
    try:
        r = s3.put_object(Bucket=BUCKET, Key=MANIFEST_KEY, Body=body, **kwargs)
    except ClientError as e:
        code = e.response["ResponseMetadata"]["HTTPStatusCode"]
        # 競合した側の /tmp には目録に無いコミットが残る。次の保存に混入させないため捨てて取り直す
        shutil.rmtree(ROOT, ignore_errors=True)
        _etag, _local = None, {}
        return {
            "push_ms": _ms(t0),
            "conflict": True,
            "http": code,
            "error": e.response["Error"]["Code"],
            "uploaded": uploaded,
            "local_discarded": True,
        }
    _etag, _seq = r["ETag"], manifest["seq"]
    _local = {rel: sha for rel, (sha, _) in cur.items()}
    lore_bytes = sum(
        cur[rel][1] for rel, sha in changed.items() if rel.startswith(".lore/") and sha in by_sha
    )
    return {
        "push_ms": _ms(t0),
        "conflict": False,
        "seq": _seq,
        "files_changed": len(changed),
        "uploaded": uploaded,
        "uploaded_bytes": uploaded_bytes,
        "lore_changed_bytes": lore_bytes,
        "dedup_hits": dedup,
        "manifest_files": len(cur),
        "manifest_bytes": len(body),
        "etag": _etag,
    }


# ---------------------------------------------- Lore(Task-8 の LoreVersionStore を写した)
class LoreStore:
    def __init__(self, root: Path) -> None:
        from lore import Lore
        from lore.types.args import LoreGlobalArgs, LoreRepositoryCreateArgs

        self.L = Lore
        self.root = root
        self.g = LoreGlobalArgs(repository_path=str(root), offline=True)
        if not (root / ".lore").exists():
            root.mkdir(parents=True, exist_ok=True)
            Lore.repository_create(
                self.g, LoreRepositoryCreateArgs(repository_url="filetto")
            ).wait()

    def _events(self, call) -> list[tuple[str, dict]]:
        from lore.types.enums import LoreEventTag

        events: list[tuple[str, dict]] = []

        def collect(event, _ctx) -> None:
            tag = LoreEventTag(event.tag).name
            data = event.get_data()
            if tag in ("REVISION_COMMIT_REVISION", "FILE_HISTORY"):
                events.append((tag, {"number": str(data.revision_number)}))
            elif tag == "METADATA" and data.key == "timestamp":
                events.append((tag, {"ms": int(data.value.cdata.numeric)}))

        call.callback(collect).wait()
        return events

    def save(self, path: str, content: bytes) -> str:
        from lore.types.args import LoreFileStageArgs, LoreRevisionCommitArgs

        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        self.L.file_stage(self.g, LoreFileStageArgs(paths=[str(target)])).wait()
        ev = self._events(self.L.revision_commit(self.g, LoreRevisionCommitArgs(message=path)))
        return next(d["number"] for t, d in ev if t == "REVISION_COMMIT_REVISION")

    def flush(self) -> None:
        from lore.types.args import LoreRepositoryFlushArgs

        self.L.repository_flush(self.g, LoreRepositoryFlushArgs()).wait()

    def versions(self, path: str) -> list[str]:
        from lore.types.args import LoreFileHistoryArgs

        if not LORE_ONLY and not (self.root / path).exists():
            return []
        ev = self._events(
            self.L.file_history(self.g, LoreFileHistoryArgs(path=str(self.root / path)))
        )
        return sorted((d["number"] for t, d in ev if t == "FILE_HISTORY"), key=int)

    def read(self, path: str, version: str) -> bytes:
        from lore.types.args import LoreFileWriteArgs

        with tempfile.TemporaryDirectory(dir=str(self.root.parent)) as tmp:
            out = Path(tmp) / "content"
            self.L.file_write(
                self.g,
                LoreFileWriteArgs(path=str(self.root / path), revision=version, output=str(out)),
            ).wait()
            return out.read_bytes()


# ---------------------------------------------------------------- handler
def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)


def _content(event: dict) -> bytes:
    if "content" in event:
        return base64.b64decode(event["content"])
    n = int(event.get("gen_bytes", 1024))
    seed = str(event.get("seed", "0")).encode()
    base = str(event.get("base", "base")).encode()
    # 本体は base から決まる擬似乱数(圧縮が効かない)。seed は末尾 64 バイトだけを変える
    # (S0-005 の「末尾を変えた版」と同じ形。重複排除の効きを見る)
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(base + counter.to_bytes(8, "big")).digest()
        counter += 1
    data = bytes(out[:n])
    return data[:-64] + seed.ljust(64, b"-") if n > 64 else data


def handler(event: dict, context) -> dict:
    global _COLD
    cold, _COLD = _COLD, False
    t_all = time.perf_counter()
    op = event.get("op", "info")
    res: dict = {"op": op, "cold": cold, "request_id": getattr(context, "aws_request_id", None)}

    if op == "info":
        import lore

        res.update(
            {
                "python": platform.python_version(),
                "machine": platform.machine(),
                "glibc": os.confstr("CS_GNU_LIBC_VERSION"),
                "lore_vcs": getattr(lore, "__version__", "?"),
                "memory_mb": getattr(context, "memory_limit_in_mb", None),
                "tmp_free_mb": shutil.disk_usage("/tmp").free // 2**20,
            }
        )
        return res | {"total_ms": _ms(t_all)}

    if op == "reset":
        shutil.rmtree(ROOT, ignore_errors=True)
        global _etag, _local
        _etag, _local = None, {}
        return res | {"total_ms": _ms(t_all)}

    res["pull"] = pull()
    t0 = time.perf_counter()
    store = LoreStore(ROOT)
    res["open_ms"] = _ms(t0)

    if op == "save":
        content = _content(event)
        t0 = time.perf_counter()
        number = store.save(event["path"], content)
        res["save_ms"] = _ms(t0)
        t0 = time.perf_counter()
        store.flush()
        res["flush_ms"] = _ms(t0)
        res["version"] = number
        res["content_sha"] = _sha(content)
        res["content_size"] = len(content)
        res["push"] = push()
    elif op == "stale_push":
        content = _content(event)
        number = store.save(event["path"], content)
        store.flush()
        res["version"] = number
        res["push"] = push(if_match='"00000000000000000000000000000000"')
    elif op == "versions":
        t0 = time.perf_counter()
        res["versions"] = store.versions(event["path"])
        res["versions_ms"] = _ms(t0)
    elif op == "read":
        t0 = time.perf_counter()
        data = store.read(event["path"], str(event["version"]))
        res["read_ms"] = _ms(t0)
        res["content_sha"] = _sha(data)
        res["content_size"] = len(data)
        res["head"] = data[:16].hex()
    else:
        raise ValueError(f"unknown op: {op}")
    return res | {"total_ms": _ms(t_all)}

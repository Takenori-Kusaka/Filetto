"""保管領域の定期検証と一時ファイルの掃除(F-001 受入基準20・21)。

Lore には保管領域の健全性検査も修復もないため(S0-005)、Filetto が版を1つずつ読み出して確かめる。
Lore は壊れた版を誤った内容で返さず読み出しを失敗させるので、読めない版を破損として記録する。
読み出しに失敗すると `.~loretemp` が残るため、保管領域から取り除く。呼び出す周期は配線の側で決める。
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from filetto.version.store import VersionNotFoundError, VersionStore, VersionStoreError

LORETEMP = ".~loretemp"


@dataclass(frozen=True)
class CorruptVersion:
    """破損した版。履歴そのものが読めず版を特定できないときは version_id が None"""

    path: str
    version_id: str | None
    detected_at: datetime


class CorruptionLog:
    """検出した破損の記録。原本の外の SQLite に置く"""

    def __init__(self, db_path: str | Path) -> None:
        self._db = Path(db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS corrupt_versions"
                " (path TEXT NOT NULL, version_id TEXT, detected_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db)

    def record(self, entry: CorruptVersion) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO corrupt_versions VALUES (?, ?, ?)",
                (entry.path, entry.version_id, entry.detected_at.isoformat()),
            )

    def list(self) -> list[CorruptVersion]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT path, version_id, detected_at FROM corrupt_versions ORDER BY rowid"
            ).fetchall()
        return [CorruptVersion(p, v, datetime.fromisoformat(at)) for p, v, at in rows]


def verify_versions(
    store: VersionStore, paths: Iterable[str], log: CorruptionLog
) -> list[CorruptVersion]:
    """各パスの版をすべて読み出し、読めない版を記録して返す"""
    found: list[CorruptVersion] = []
    for path in paths:
        try:
            versions = store.versions(path)
        except VersionStoreError:
            found.append(CorruptVersion(path, None, datetime.now(UTC)))
            continue
        for version in versions:
            try:
                store.read(path, version.id)
            except (VersionStoreError, VersionNotFoundError):
                found.append(CorruptVersion(path, version.id, datetime.now(UTC)))
    for entry in found:
        log.record(entry)
    return found


def remove_loretemp(store_root: str | Path) -> list[str]:
    """保管領域に残った `.~loretemp`(ファイルかディレクトリ)を消し、消したものの相対パスを返す。
    シンボリックリンクはたどらず、リンクそのものだけを消す"""
    root = Path(store_root)
    removed: list[str] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        base = Path(current)
        for name in [d for d in dirs if d.endswith(LORETEMP)]:
            target = base / name
            if target.is_symlink():
                target.unlink()
            else:
                shutil.rmtree(target)
            dirs.remove(name)
            removed.append(target.relative_to(root).as_posix())
        for name in [f for f in files if f.endswith(LORETEMP)]:
            (base / name).unlink()
            removed.append((base / name).relative_to(root).as_posix())
    return removed

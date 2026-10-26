"""原本の上書きの検知(F-001 受入基準15)。

上書きは Filetto の外(エディタなど)で起こる。上書きに気づいた時点で更新前の内容は残って
いないため、走査で初めて見たときの内容を版として保管し、変更を検知するたびに新しい版を
保管する。これで、どの上書きについても更新前の内容が版として残る(2026-10-26 の判断)。
変更は大きさと更新時刻で検知する。走査の状態は原本の外の SQLite に置く。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from filetto.storage import OriginalStore
from filetto.version.store import VersionStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    path TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL
)
"""


class OverwriteWatcher:
    def __init__(self, original: OriginalStore, store: VersionStore, db_path: str | Path) -> None:
        db = Path(db_path).resolve()
        if db.is_relative_to(original.root):
            raise ValueError(f"走査の状態は原本ディレクトリの外に置く: {db_path}")
        db.parent.mkdir(parents=True, exist_ok=True)
        self._db = db
        self._original = original
        self._store = store
        conn = sqlite3.connect(self._db)
        try:
            conn.executescript(_SCHEMA)
        finally:
            conn.close()

    def _files(self, rel: str = ""):
        for entry in self._original.list(rel):
            if entry.is_dir:
                yield from self._files(entry.path)
            else:
                yield entry

    def scan(self) -> list[str]:
        """原本を走査し、初めて見たファイルと変わったファイルを版として保管する。保管したパスを返す"""
        saved = []
        conn = sqlite3.connect(self._db)
        try:
            for entry in self._files():
                row = conn.execute(
                    "SELECT size, mtime_ns FROM seen WHERE path = ?", (entry.path,)
                ).fetchone()
                if row == (entry.size, entry.mtime_ns):
                    continue
                self._store.save(entry.path, self._original.read_bytes(entry.path))
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO seen (path, size, mtime_ns) VALUES (?, ?, ?)",
                        (entry.path, entry.size, entry.mtime_ns),
                    )
                saved.append(entry.path)
        finally:
            conn.close()
        return saved

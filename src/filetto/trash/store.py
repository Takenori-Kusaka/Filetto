"""ゴミ箱の記録(F-001 受入基準2)。

削除は論理削除であり、原本の実体には触れない(受入基準1)。ゴミ箱に入ったことは、
原本ディレクトリの外に置く SQLite のメタデータへ記録する。実体を複製・移動しないため、
削除はメタデータの更新だけで完了する。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from filetto.storage import OriginalStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trash (
    path TEXT PRIMARY KEY,
    trashed_at TEXT NOT NULL
)
"""


class AlreadyTrashedError(ValueError):
    """指定されたパスは既にゴミ箱に入っている"""


@dataclass(frozen=True)
class TrashEntry:
    """ゴミ箱の1項目。path は原本ディレクトリからの相対パス(削除前のパス)"""

    path: str
    trashed_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


class TrashStore:
    def __init__(
        self,
        db_path: str | Path,
        original: OriginalStore,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        db = Path(db_path).resolve()
        if db.is_relative_to(original.root):
            raise ValueError(f"ゴミ箱の記録は原本ディレクトリの外に置く: {db_path}")
        db.parent.mkdir(parents=True, exist_ok=True)
        self._db = db
        self._original = original
        self._clock = clock
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def trash(self, rel: str) -> TrashEntry:
        """ゴミ箱へ入れる。原本に無いパスは FileNotFoundError、原本の外は OutsideOriginalError"""
        path = self._original.stat(rel).path
        entry = TrashEntry(path=path, trashed_at=self._clock())
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO trash (path, trashed_at) VALUES (?, ?)",
                    (entry.path, entry.trashed_at.isoformat()),
                )
        except sqlite3.IntegrityError as e:
            raise AlreadyTrashedError(f"既にゴミ箱に入っている: {path}") from e
        return entry

    def contains(self, rel: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM trash WHERE path = ?", (rel,)).fetchone()
        return row is not None

    def list(self) -> list[TrashEntry]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path, trashed_at FROM trash ORDER BY path").fetchall()
        return [TrashEntry(path=p, trashed_at=datetime.fromisoformat(t)) for p, t in rows]

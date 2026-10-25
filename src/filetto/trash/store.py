"""ゴミ箱の記録(F-001 受入基準2)。

削除は論理削除であり、原本の実体には触れない(受入基準1)。ゴミ箱に入ったことは、
原本ディレクトリの外に置く SQLite のメタデータへ記録する。実体を複製・移動しないため、
削除はメタデータの更新だけで完了する。

復元(受入基準5)は記録を外すことで、ファイルを削除前のパスへ戻す。ゴミ箱へ入れた時点の
実体の識別(大きさと更新時刻)も記録し、復元の時点で同じパスに別のファイルが置かれていれば、
同名の衝突として復元しない(受入基準6)。

保持期間(受入基準7)を過ぎた項目は、ゴミ箱を読むたびに完全削除する。完全削除は Filetto の
管理から外すことであり、原本の実体は消さない(受入基準1)。完全削除したパスは purged に残し、
ゴミ箱へ戻すことも復元することもできない。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from filetto.config import load_retention
from filetto.storage import OriginalStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trash (
    path TEXT PRIMARY KEY,
    trashed_at TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS purged (
    path TEXT PRIMARY KEY,
    purged_at TEXT NOT NULL
)
"""


class AlreadyTrashedError(ValueError):
    """指定されたパスは既にゴミ箱に入っている"""


class NotTrashedError(LookupError):
    """指定されたパスはゴミ箱に入っていない"""


class RestoreConflictError(ValueError):
    """復元先のパスに、ゴミ箱へ入れたものとは別のファイルが置かれている"""


@dataclass(frozen=True)
class TrashEntry:
    """ゴミ箱の1項目。path は原本ディレクトリからの相対パス(削除前のパス)"""

    path: str
    trashed_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


_FROM_ENV = object()


class TrashStore:
    def __init__(
        self,
        db_path: str | Path,
        original: OriginalStore,
        clock: Callable[[], datetime] = _now,
        retention: timedelta | None | object = _FROM_ENV,
    ) -> None:
        """retention は保持期間。None は無期限。省略すると環境変数から読む"""
        db = Path(db_path).resolve()
        if db.is_relative_to(original.root):
            raise ValueError(f"ゴミ箱の記録は原本ディレクトリの外に置く: {db_path}")
        db.parent.mkdir(parents=True, exist_ok=True)
        self._db = db
        self._original = original
        self._clock = clock
        self._retention = load_retention() if retention is _FROM_ENV else retention
        conn = sqlite3.connect(self._db)
        try:
            conn.executescript(_SCHEMA)
        finally:
            conn.close()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db)
        try:
            with conn:
                self._purge_expired(conn)
                yield conn
        finally:
            conn.close()

    def _purge_expired(self, conn: sqlite3.Connection) -> None:
        if self._retention is None:
            return
        now = self._clock()
        cutoff = (now - self._retention).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO purged (path, purged_at) "
            "SELECT path, ? FROM trash WHERE trashed_at < ?",
            (now.isoformat(), cutoff),
        )
        conn.execute("DELETE FROM trash WHERE trashed_at < ?", (cutoff,))

    def trash(self, rel: str) -> TrashEntry:
        """ゴミ箱へ入れる。原本に無いパスは FileNotFoundError、原本の外は OutsideOriginalError"""
        stat = self._original.stat(rel)
        path = stat.path
        entry = TrashEntry(path=path, trashed_at=self._clock())
        try:
            with self._connect() as conn:
                if conn.execute("SELECT 1 FROM purged WHERE path = ?", (path,)).fetchone():
                    raise FileNotFoundError(f"完全削除済み: {path}")
                conn.execute(
                    "INSERT INTO trash (path, trashed_at, size, mtime_ns) VALUES (?, ?, ?, ?)",
                    (entry.path, entry.trashed_at.isoformat(), stat.size, stat.mtime_ns),
                )
        except sqlite3.IntegrityError as e:
            raise AlreadyTrashedError(f"既にゴミ箱に入っている: {path}") from e
        return entry

    def restore(self, rel: str) -> TrashEntry:
        """削除前のパスへ戻す。ゴミ箱に無ければ NotTrashedError、同名の別ファイルがあれば
        RestoreConflictError(どちらも復元しない)。削除前のパスの実体が無ければ FileNotFoundError"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT path, trashed_at, size, mtime_ns FROM trash WHERE path = ?", (rel,)
            ).fetchone()
            if row is None:
                raise NotTrashedError(f"ゴミ箱に入っていない: {rel}")
            path, trashed_at, size, mtime_ns = row
            current = self._original.stat(path)
            if (current.size, current.mtime_ns) != (size, mtime_ns):
                raise RestoreConflictError(f"復元先に同名の別ファイルがある: {path}")
            conn.execute("DELETE FROM trash WHERE path = ?", (path,))
        return TrashEntry(path=path, trashed_at=datetime.fromisoformat(trashed_at))

    def contains(self, rel: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM trash WHERE path = ?", (rel,)).fetchone()
        return row is not None

    def list(self) -> list[TrashEntry]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path, trashed_at FROM trash ORDER BY path").fetchall()
        return [TrashEntry(path=p, trashed_at=datetime.fromisoformat(t)) for p, t in rows]

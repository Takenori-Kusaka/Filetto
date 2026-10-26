"""リネーム・移動と操作履歴(F-001 受入基準13・14、監査ログ)。

リネームと移動は論理的な操作であり、原本の実体には触れない(受入基準1)。原本の外に置く
SQLite に「いまのパス → 原本のパス」の対応を記録し、メタデータの更新だけで完了する。

操作履歴は監査ログを兼ねる。削除・リネーム・移動について、実行時刻・操作種別・変更前と
変更後のパス・呼び出し経路(webui / mcp)を記録する。変更前のパスが受入基準13・14 の記録になる。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from filetto.storage import OriginalStore, OutsideOriginalError

Op = Literal["delete", "rename", "move"]
Via = Literal["webui", "mcp"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS relocated (
    current TEXT PRIMARY KEY,
    original TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    op TEXT NOT NULL,
    before TEXT NOT NULL,
    after TEXT,
    via TEXT NOT NULL
)
"""


class RelocateConflictError(ValueError):
    """リネーム・移動の先に、既にファイルがある"""


@dataclass(frozen=True)
class HistoryEntry:
    at: datetime
    op: Op
    before: str
    # 削除では None
    after: str | None
    via: Via


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize(rel: str) -> str:
    """原本ディレクトリからの相対パスとして正規化する。原本の外を指すものは拒否する"""
    path = PurePosixPath(rel)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise OutsideOriginalError(f"原本ディレクトリの外を指している: {rel}")
    return path.as_posix()


class HistoryStore:
    def __init__(
        self,
        db_path: str | Path,
        original: OriginalStore,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        db = Path(db_path).resolve()
        if db.is_relative_to(original.root):
            raise ValueError(f"操作履歴は原本ディレクトリの外に置く: {db_path}")
        db.parent.mkdir(parents=True, exist_ok=True)
        self._db = db
        self._original = original
        self._clock = clock
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
                yield conn
        finally:
            conn.close()

    def _resolve(self, conn: sqlite3.Connection, current: str) -> str | None:
        """いまのパスに当たる原本のパス。リネーム・移動で離れたパスなら None"""
        row = conn.execute("SELECT original FROM relocated WHERE current = ?", (current,))
        if found := row.fetchone():
            return found[0]
        away = conn.execute("SELECT 1 FROM relocated WHERE original = ?", (current,))
        return None if away.fetchone() else current

    def resolve(self, current: str) -> str:
        """いまのパスに当たる原本のパス。見つからなければ FileNotFoundError"""
        path = _normalize(current)
        with self._connect() as conn:
            original = self._resolve(conn, path)
        if original is None:
            raise FileNotFoundError(f"リネーム・移動で離れたパス: {current}")
        self._original.stat(original)
        return original

    def _occupied(self, conn: sqlite3.Connection, path: str) -> bool:
        original = self._resolve(conn, path)
        if original is None or original != path:
            return original is not None
        return (self._original.root / path).exists()

    def rename(self, current: str, name: str, via: Via) -> str:
        """名前だけを変える。返り値はいまのパス"""
        if not name or "/" in name or name in (".", ".."):
            raise ValueError(f"名前にパスの区切りは使えない: {name}")
        parent = PurePosixPath(_normalize(current)).parent
        return self._relocate(current, (parent / name).as_posix(), "rename", via)

    def move(self, current: str, to: str, via: Via) -> str:
        """原本ディレクトリの中の別のディレクトリへ移す。返り値はいまのパス"""
        directory = _normalize(to) if to not in ("", ".") else "."
        if not self._original.stat(directory).is_dir:
            raise NotADirectoryError(f"移動先がディレクトリでない: {to}")
        name = PurePosixPath(_normalize(current)).name
        return self._relocate(current, (PurePosixPath(directory) / name).as_posix(), "move", via)

    def _relocate(self, current: str, new: str, op: Op, via: Via) -> str:
        before = _normalize(current)
        original = self.resolve(before)
        with self._connect() as conn:
            if self._occupied(conn, new):
                raise RelocateConflictError(f"移動先に既にファイルがある: {new}")
            conn.execute("DELETE FROM relocated WHERE original = ?", (original,))
            if new != original:
                conn.execute(
                    "INSERT INTO relocated (current, original) VALUES (?, ?)", (new, original)
                )
            self._record(conn, op, before, new, via)
        return new

    def record_delete(self, path: str, via: Via) -> None:
        with self._connect() as conn:
            self._record(conn, "delete", _normalize(path), None, via)

    def _record(self, conn: sqlite3.Connection, op: Op, before: str, after: str | None, via: Via):
        conn.execute(
            "INSERT INTO history (at, op, before, after, via) VALUES (?, ?, ?, ?, ?)",
            (self._clock().isoformat(), op, before, after, via),
        )

    def list(self) -> list[HistoryEntry]:
        """操作の古い順"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT at, op, before, after, via FROM history ORDER BY id"
            ).fetchall()
        return [
            HistoryEntry(datetime.fromisoformat(at), op, before, after, via)
            for at, op, before, after, via in rows
        ]

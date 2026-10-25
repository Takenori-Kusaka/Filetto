"""F-001 受入基準7 の検査(保持期間の経過による完全削除)。

受入基準7: ファイルがゴミ箱へ入ってから保持期間を経過した場合、
システムは当該ファイルを完全に削除しなければならない。

完全削除は「Filetto の管理から外す」と解釈する(受入基準1 により原本は書き換えない)。
完全削除した項目は、ゴミ箱の一覧に出ず、復元できず、原本の実体は残る。
受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from filetto.storage import OriginalStore
from filetto.trash import NotTrashedError, TrashStore

T0 = datetime(2026, 10, 1, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    (root / "b.txt").write_text("b", encoding="utf-8")
    return root


@pytest.fixture
def clock() -> Clock:
    return Clock()


def _store(tmp_path: Path, original: Path, clock: Clock, retention: timedelta | None):
    return TrashStore(
        tmp_path / "meta" / "f.db", OriginalStore(original), clock=clock, retention=retention
    )


def test_entry_past_retention_is_purged(tmp_path: Path, original: Path, clock: Clock) -> None:
    trash = _store(tmp_path, original, clock, timedelta(days=30))
    trash.trash("a.txt")

    clock.now = T0 + timedelta(days=30, seconds=1)

    assert trash.list() == []
    assert not trash.contains("a.txt")
    with pytest.raises(NotTrashedError):
        trash.restore("a.txt")


def test_entry_within_retention_stays(tmp_path: Path, original: Path, clock: Clock) -> None:
    trash = _store(tmp_path, original, clock, timedelta(days=30))
    trash.trash("a.txt")
    clock.now = T0 + timedelta(days=29)
    trash.trash("b.txt")

    clock.now = T0 + timedelta(days=30, seconds=1)

    assert [e.path for e in trash.list()] == ["b.txt"]


def test_unlimited_retention_never_purges(tmp_path: Path, original: Path, clock: Clock) -> None:
    trash = _store(tmp_path, original, clock, None)
    trash.trash("a.txt")

    clock.now = T0 + timedelta(days=36500)

    assert [e.path for e in trash.list()] == ["a.txt"]


def test_purge_keeps_the_original_entity(tmp_path: Path, original: Path, clock: Clock) -> None:
    before = _snapshot(original)
    trash = _store(tmp_path, original, clock, timedelta(days=1))
    trash.trash("a.txt")

    clock.now = T0 + timedelta(days=2)
    trash.list()

    assert _snapshot(original) == before


def test_purged_file_does_not_come_back_into_filetto(
    tmp_path: Path, original: Path, clock: Clock
) -> None:
    trash = _store(tmp_path, original, clock, timedelta(days=1))
    trash.trash("a.txt")
    clock.now = T0 + timedelta(days=2)
    trash.list()

    with pytest.raises(FileNotFoundError):
        trash.trash("a.txt")

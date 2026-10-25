"""F-001 受入基準11 の検査(残日数の計算)。受入基準だけを入力に書いた検査です。

受入基準11: 利用者がゴミ箱の一覧を開いた場合、システムは各項目に完全削除までの残日数を
表示しなければならない。残日数は日の途中を切り上げる(最後の1日は「残り1日」と出す)。
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from filetto.storage import OriginalStore
from filetto.trash import TrashStore

T0 = datetime(2026, 10, 1, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    return root


def _store(tmp_path: Path, original: Path, clock: Clock, retention: timedelta | None):
    return TrashStore(
        tmp_path / "meta" / "f.db", OriginalStore(original), clock=clock, retention=retention
    )


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        (timedelta(0), 30),
        (timedelta(days=10), 20),
        (timedelta(days=29, hours=12), 1),
        (timedelta(days=30), 0),
    ],
)
def test_remaining_days_until_purge(
    tmp_path: Path, original: Path, elapsed: timedelta, expected: int
) -> None:
    clock = Clock()
    trash = _store(tmp_path, original, clock, timedelta(days=30))
    entry = trash.trash("a.txt")

    clock.now = T0 + elapsed

    assert trash.remaining_days(entry) == expected


def test_unlimited_retention_has_no_remaining_days(tmp_path: Path, original: Path) -> None:
    clock = Clock()
    trash = _store(tmp_path, original, clock, None)
    entry = trash.trash("a.txt")

    assert trash.remaining_days(entry) is None

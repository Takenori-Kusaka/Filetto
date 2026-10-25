"""F-001 受入基準5・6 の検査(ゴミ箱の本体)。受入基準だけを入力に書いた検査です。"""

from pathlib import Path

import pytest

from filetto.storage import OriginalStore
from filetto.trash import NotTrashedError, RestoreConflictError, TrashStore


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    return root


@pytest.fixture
def trash(tmp_path: Path, original: Path) -> TrashStore:
    return TrashStore(tmp_path / "meta" / "f.db", OriginalStore(original))


def test_restore_takes_the_entry_out_of_trash(trash: TrashStore) -> None:
    trash.trash("a.txt")

    restored = trash.restore("a.txt")

    assert restored.path == "a.txt"
    assert not trash.contains("a.txt")
    assert trash.list() == []


def test_restore_of_an_entry_not_in_trash_fails(trash: TrashStore) -> None:
    with pytest.raises(NotTrashedError):
        trash.restore("a.txt")


def test_restore_onto_a_different_file_at_the_same_path_conflicts(
    trash: TrashStore, original: Path
) -> None:
    trash.trash("a.txt")
    (original / "a.txt").write_text("置き換えた別の内容", encoding="utf-8")

    with pytest.raises(RestoreConflictError):
        trash.restore("a.txt")
    assert trash.contains("a.txt")

"""F-001 受入基準2 の検査(ゴミ箱の本体。WebUI の入口の検査は tests/api/ に置く)。

受入基準2: 利用者が WebUI からファイルの削除を実行した場合、
システムはファイルをゴミ箱へ移動し、原本の実体を削除してはならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from filetto.storage import OriginalStore, OutsideOriginalError
from filetto.trash import AlreadyTrashedError, TrashStore

FIXED = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)


def _snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {
        str(p.relative_to(root)): (
            hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "",
            p.lstat().st_mtime_ns,
        )
        for p in sorted(root.rglob("*"))
    }


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("あいう", encoding="utf-8")
    (root / "sub" / "b.txt").write_text("b", encoding="utf-8")
    return root


@pytest.fixture
def store(tmp_path: Path, original: Path) -> TrashStore:
    db = tmp_path / "meta" / "filetto.db"
    return TrashStore(db, OriginalStore(original), clock=lambda: FIXED)


def test_deleted_file_goes_to_trash(store: TrashStore) -> None:
    entry = store.trash("sub/b.txt")

    assert entry.path == "sub/b.txt"
    assert entry.trashed_at == FIXED
    assert [e.path for e in store.list()] == ["sub/b.txt"]
    assert store.contains("sub/b.txt")
    assert not store.contains("a.txt")


def test_original_entity_is_not_deleted(store: TrashStore, original: Path) -> None:
    before = _snapshot(original)

    store.trash("a.txt")
    store.trash("sub/b.txt")

    assert (original / "a.txt").read_text(encoding="utf-8") == "あいう"
    assert (original / "sub" / "b.txt").read_text(encoding="utf-8") == "b"
    assert _snapshot(original) == before


def test_trash_survives_restart(tmp_path: Path, original: Path) -> None:
    db = tmp_path / "meta" / "filetto.db"
    TrashStore(db, OriginalStore(original), clock=lambda: FIXED).trash("a.txt")

    reopened = TrashStore(db, OriginalStore(original))
    assert [(e.path, e.trashed_at) for e in reopened.list()] == [("a.txt", FIXED)]


def test_trashing_twice_is_refused(store: TrashStore) -> None:
    store.trash("a.txt")
    with pytest.raises(AlreadyTrashedError):
        store.trash("a.txt")
    assert [e.path for e in store.list()] == ["a.txt"]


def test_missing_file_is_refused(store: TrashStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.trash("missing.txt")
    assert store.list() == []


def test_path_outside_original_is_refused(store: TrashStore) -> None:
    with pytest.raises(OutsideOriginalError):
        store.trash("../outside.txt")


def test_trash_metadata_is_kept_outside_the_original(tmp_path: Path, original: Path) -> None:
    with pytest.raises(ValueError):
        TrashStore(original / "filetto.db", OriginalStore(original))
    assert not (original / "filetto.db").exists()

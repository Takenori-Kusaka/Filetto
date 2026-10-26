"""F-001 受入基準15・17 の検査(Lore を使う VersionStore の実装)。

受入基準15: ファイルが上書き更新された場合、システムは更新前の内容をバージョンとして
保管しなければならない。
受入基準17: システムはバージョン保管の呼び出しを VersionStore インターフェースの背後で行い、
Lore の型・イベント・エラーを他の層へ渡してはならない。

受入基準と計画だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

from filetto.storage import OriginalStore
from filetto.version import LoreVersionStore, OverwriteWatcher, VersionNotFoundError


@pytest.fixture
def store(tmp_path: Path) -> LoreVersionStore:
    return LoreVersionStore(tmp_path / "lore")


def test_saved_contents_can_be_read_back_per_version(store: LoreVersionStore) -> None:
    v1 = store.save("docs/a.txt", b"v1")
    v2 = store.save("docs/a.txt", b"v2")

    assert [v.id for v in store.versions("docs/a.txt")] == [v1.id, v2.id]
    assert store.read("docs/a.txt", v1.id) == b"v1"
    assert store.read("docs/a.txt", v2.id) == b"v2"


def test_versions_are_kept_per_path(store: LoreVersionStore) -> None:
    store.save("docs/a.txt", b"a")
    store.save("b.txt", b"b")
    assert len(store.versions("docs/a.txt")) == 1
    assert store.versions("none.txt") == []


def test_versions_survive_reopening_the_store(tmp_path: Path) -> None:
    saved = LoreVersionStore(tmp_path / "lore").save("a.txt", b"x")
    reopened = LoreVersionStore(tmp_path / "lore")
    assert reopened.read("a.txt", saved.id) == b"x"


def test_versions_expose_only_plain_values(store: LoreVersionStore) -> None:
    """Lore の型を外へ渡さない(受入基準17)"""
    version = store.save("a.txt", b"x")
    listed = store.versions("a.txt")[0]
    for v in (version, listed):
        assert type(v.id) is str
        assert type(v.path) is str
        assert isinstance(v.saved_at, datetime)
        assert v.saved_at.tzinfo is not None


def test_lore_errors_are_not_passed_to_other_layers(store: LoreVersionStore) -> None:
    """存在しない版は Filetto の例外で返す。Lore の例外を外へ渡さない(受入基準17)"""
    store.save("a.txt", b"x")
    for path, version_id in (("a.txt", "999"), ("none.txt", "1")):
        with pytest.raises(VersionNotFoundError) as raised:
            store.read(path, version_id)
        assert type(raised.value).__module__.startswith("filetto.")


def test_overwrite_in_the_original_is_kept_in_lore(tmp_path: Path) -> None:
    original = tmp_path / "original"
    original.mkdir()
    target = original / "a.txt"
    target.write_text("v1", encoding="utf-8")
    store = LoreVersionStore(tmp_path / "lore")
    watcher = OverwriteWatcher(OriginalStore(original), store, tmp_path / "meta" / "f.db")

    watcher.scan()
    mtime = target.stat().st_mtime_ns
    target.write_text("v2", encoding="utf-8")
    os.utime(target, ns=(mtime + 1_000_000_000, mtime + 1_000_000_000))
    watcher.scan()

    contents = [store.read("a.txt", v.id) for v in store.versions("a.txt")]
    assert contents == [b"v1", b"v2"]

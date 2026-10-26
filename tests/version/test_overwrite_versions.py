"""F-001 受入基準15・17 の検査(版の保管)。

受入基準15: ファイルが上書き更新された場合、システムは更新前の内容をバージョンとして
保管しなければならない。
受入基準17: システムはバージョン保管の呼び出しを VersionStore インターフェースの背後で行い、
Lore の型・イベント・エラーを他の層へ渡してはならない。

上書きは Filetto の外(エディタなど)で起こる(2026-10-26 の判断: 外部の上書きを検知して版にする)。
走査で初めて見た内容を版として保管し、変更を検知するたびに新しい版を保管する。
受入基準と計画だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import hashlib
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from filetto.storage import OriginalStore
from filetto.version import OverwriteWatcher, Version

SRC = Path(__file__).resolve().parents[2] / "src" / "filetto"


class FakeVersionStore:
    """VersionStore の検査用の実装(メモリに置く)"""

    def __init__(self) -> None:
        self.saved: dict[str, list[tuple[Version, bytes]]] = {}

    def save(self, path: str, content: bytes) -> Version:
        version = Version(
            id=f"v{sum(map(len, self.saved.values()))}", path=path, saved_at=datetime.now(UTC)
        )
        self.saved.setdefault(path, []).append((version, content))
        return version

    def versions(self, path: str) -> list[Version]:
        return [v for v, _ in self.saved.get(path, [])]

    def read(self, path: str, version_id: str) -> bytes:
        return next(c for v, c in self.saved[path] if v.id == version_id)


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _overwrite(path: Path, text: str) -> None:
    """外のエディタでの上書きを模す。更新時刻を確実に進める"""
    before = path.stat().st_mtime_ns
    path.write_text(text, encoding="utf-8")
    os.utime(path, ns=(before + 1_000_000_000, before + 1_000_000_000))


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "a.txt").write_text("v1", encoding="utf-8")
    return root


@pytest.fixture
def store() -> FakeVersionStore:
    return FakeVersionStore()


@pytest.fixture
def watcher(tmp_path: Path, original: Path, store: FakeVersionStore) -> OverwriteWatcher:
    return OverwriteWatcher(OriginalStore(original), store, tmp_path / "meta" / "f.db")


def test_content_before_an_overwrite_is_kept_as_a_version(
    watcher: OverwriteWatcher, store: FakeVersionStore, original: Path
) -> None:
    watcher.scan()
    _overwrite(original / "docs" / "a.txt", "v2")
    watcher.scan()

    contents = [store.read("docs/a.txt", v.id) for v in store.versions("docs/a.txt")]
    assert b"v1" in contents
    assert contents[-1] == b"v2"


def test_unchanged_file_does_not_add_a_version(
    watcher: OverwriteWatcher, store: FakeVersionStore
) -> None:
    watcher.scan()
    count = len(store.versions("docs/a.txt"))
    watcher.scan()
    assert len(store.versions("docs/a.txt")) == count


def test_scan_reports_the_paths_it_saved(watcher: OverwriteWatcher, original: Path) -> None:
    assert watcher.scan() == ["docs/a.txt"]
    assert watcher.scan() == []
    _overwrite(original / "docs" / "a.txt", "v2")
    assert watcher.scan() == ["docs/a.txt"]


def test_scan_state_survives_a_restart(
    tmp_path: Path, original: Path, store: FakeVersionStore
) -> None:
    db = tmp_path / "meta" / "f.db"
    OverwriteWatcher(OriginalStore(original), store, db).scan()
    assert OverwriteWatcher(OriginalStore(original), store, db).scan() == []


def test_scan_does_not_write_the_original(watcher: OverwriteWatcher, original: Path) -> None:
    before = _snapshot(original)
    watcher.scan()
    assert _snapshot(original) == before


def test_scan_state_is_kept_outside_the_original(original: Path, store: FakeVersionStore) -> None:
    with pytest.raises(ValueError):
        OverwriteWatcher(OriginalStore(original), store, original / "f.db")


def test_lore_is_used_only_behind_the_version_package() -> None:
    """Lore の SDK(import lore)を filetto.version の外から使わない(受入基準17)"""
    pattern = re.compile(r"^\s*(import lore|from lore\b)", re.M)
    outside = [
        str(p)
        for p in SRC.rglob("*.py")
        if "version" not in p.relative_to(SRC).parts and pattern.search(p.read_text("utf-8"))
    ]
    assert outside == []

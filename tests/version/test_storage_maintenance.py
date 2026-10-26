"""F-001 受入基準20・21 の検査(保管領域の定期検証と一時ファイルの掃除)。

受入基準20: 保管領域の定期検証で破損を検出した場合、システムは破損したバージョンの
識別子を記録しなければならない。
受入基準21: 保管領域に `.~loretemp` が残存している場合、システムは当該ディレクトリを
削除しなければならない。
受入基準17 により、検証の途中でも Lore の例外を外へ渡さない。

S0-005 の観察: Lore は破損した版を誤った内容で返さず、読み出しを失敗させる。
`.~loretemp` は読み出しに失敗したときに残る一時ファイル(または一時ディレクトリ)。
受入基準と計画だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from filetto.version import (
    CorruptionLog,
    LoreVersionStore,
    Version,
    VersionNotFoundError,
    VersionStoreError,
    remove_loretemp,
    verify_versions,
)


class FakeVersionStore:
    """版ごとに、読めるか・壊れているかを決められる VersionStore"""

    def __init__(self) -> None:
        self.contents: dict[str, dict[str, bytes | None]] = {}
        self.unreadable_history: set[str] = set()

    def add(self, path: str, version_id: str, content: bytes | None) -> None:
        self.contents.setdefault(path, {})[version_id] = content

    def save(self, path: str, content: bytes) -> Version:
        raise NotImplementedError

    def versions(self, path: str) -> list[Version]:
        if path in self.unreadable_history:
            raise VersionStoreError(f"履歴が読めない: {path}")
        now = datetime.now(UTC)
        return [Version(id=i, path=path, saved_at=now) for i in self.contents.get(path, {})]

    def read(self, path: str, version_id: str) -> bytes:
        content = self.contents.get(path, {}).get(version_id)
        if version_id not in self.contents.get(path, {}):
            raise VersionNotFoundError(version_id)
        if content is None:
            raise VersionStoreError(f"版が読めない: {path}@{version_id}")
        return content


@pytest.fixture
def log(tmp_path: Path) -> CorruptionLog:
    return CorruptionLog(tmp_path / "meta" / "f.db")


def test_corrupt_version_id_is_recorded(log: CorruptionLog) -> None:
    store = FakeVersionStore()
    store.add("docs/a.txt", "1", b"v1")
    store.add("docs/a.txt", "2", None)
    store.add("b.txt", "3", b"b")

    found = verify_versions(store, ["docs/a.txt", "b.txt"], log)

    assert [(c.path, c.version_id) for c in found] == [("docs/a.txt", "2")]
    assert [(c.path, c.version_id) for c in log.list()] == [("docs/a.txt", "2")]


def test_healthy_storage_records_nothing(log: CorruptionLog) -> None:
    store = FakeVersionStore()
    store.add("a.txt", "1", b"x")
    assert verify_versions(store, ["a.txt"], log) == []
    assert log.list() == []


def test_unreadable_history_is_recorded_without_a_version_id(log: CorruptionLog) -> None:
    """版の一覧そのものが読めないときは、識別子を特定できないことを記録する"""
    store = FakeVersionStore()
    store.unreadable_history.add("a.txt")
    found = verify_versions(store, ["a.txt"], log)
    assert [(c.path, c.version_id) for c in found] == [("a.txt", None)]


def test_record_has_detection_time_and_survives_reopening(tmp_path: Path) -> None:
    store = FakeVersionStore()
    store.add("a.txt", "1", None)
    start = datetime.now(UTC)
    verify_versions(store, ["a.txt"], CorruptionLog(tmp_path / "meta" / "f.db"))

    (entry,) = CorruptionLog(tmp_path / "meta" / "f.db").list()
    assert entry.detected_at.tzinfo is not None
    assert start <= entry.detected_at <= datetime.now(UTC)


def _packs(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.parent.name == "pack")


def _flip(path: Path) -> None:
    path.write_bytes(bytes(b ^ 0xFF for b in path.read_bytes()))


def test_lore_corruption_of_one_version_is_detected(tmp_path: Path, log: CorruptionLog) -> None:
    """Lore の保管領域で1つの版の内容が壊れたとき、その版の識別子を記録する"""
    base = tmp_path / "base"
    store = LoreVersionStore(base)
    store.save("a.txt", b"hello world " * 1000)
    store.save("a.txt", b"second " * 1000)

    # どの pack がどの版の内容を持つかは内容のハッシュで決まるため、1つずつ壊して探す
    for pack in _packs(base):
        work = tmp_path / "work"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(base, work)
        _flip(work / pack.relative_to(base))
        found = verify_versions(LoreVersionStore(work), ["a.txt"], log)
        if len(found) == 1 and found[0].version_id is not None:
            assert found[0].path == "a.txt"
            assert found[0].version_id in {"1", "2"}
            return
    pytest.fail("1つの版だけが壊れる pack が見つからない")


def test_lore_errors_do_not_escape_when_the_history_is_broken(tmp_path: Path) -> None:
    root = tmp_path / "lore"
    store = LoreVersionStore(root)
    store.save("a.txt", b"x" * 1000)
    for pack in _packs(root):
        _flip(pack)

    reopened = LoreVersionStore(root)
    with pytest.raises(VersionStoreError) as raised:
        reopened.versions("a.txt")
    assert type(raised.value).__module__.startswith("filetto.")


def test_loretemp_left_in_the_storage_is_removed(tmp_path: Path) -> None:
    root = tmp_path / "lore"
    (root / "docs" / "big.pdf.~loretemp").mkdir(parents=True)
    (root / "docs" / "big.pdf.~loretemp" / "part").write_bytes(b"x")
    (root / "c.txt.~loretemp").write_bytes(b"y")
    (root / "docs" / "keep.txt").write_bytes(b"k")

    removed = remove_loretemp(root)

    assert sorted(removed) == ["c.txt.~loretemp", "docs/big.pdf.~loretemp"]
    assert not (root / "docs" / "big.pdf.~loretemp").exists()
    assert not (root / "c.txt.~loretemp").exists()
    assert (root / "docs" / "keep.txt").read_bytes() == b"k"


def test_loretemp_outside_the_storage_is_not_touched(tmp_path: Path) -> None:
    root = tmp_path / "lore"
    root.mkdir()
    outside = tmp_path / "other.~loretemp"
    outside.write_bytes(b"z")
    (root / "link.~loretemp").symlink_to(outside)

    remove_loretemp(root)

    assert outside.read_bytes() == b"z"

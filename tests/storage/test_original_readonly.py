"""F-001 受入基準1 の検査。

受入基準1: システムは原本ディレクトリに対して読み取りのみを行い、
原本ファイルを書き換えてはならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import builtins
import hashlib
import io
import os
import stat
from pathlib import Path

import pytest

from filetto.storage import OriginalStore, OutsideOriginalError


def _snapshot(root: Path) -> dict[str, tuple[str, int, int]]:
    """原本ディレクトリの全ファイルの内容の要約値・更新時刻・権限。書き換えの有無を比べるために使う"""
    snap = {}
    for p in sorted(root.rglob("*")):
        st = p.lstat()
        digest = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""
        snap[str(p.relative_to(root))] = (digest, st.st_mtime_ns, st.st_mode)
    return snap


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("あいう", encoding="utf-8")
    (root / "sub" / "b.bin").write_bytes(b"\x00\x01\x02")
    return root


def test_reads_contents_and_lists_entries(original: Path) -> None:
    store = OriginalStore(original)

    assert store.read_bytes("a.txt") == "あいう".encode()
    assert store.read_bytes("sub/b.bin") == b"\x00\x01\x02"
    assert {e.path for e in store.list("")} == {"a.txt", "sub"}
    assert {e.path for e in store.list("sub")} == {"sub/b.bin"}
    assert store.stat("sub/b.bin").size == 3


def test_reading_does_not_change_the_original(original: Path) -> None:
    before = _snapshot(original)
    store = OriginalStore(original)

    store.list("")
    store.list("sub")
    store.read_bytes("a.txt")
    store.stat("sub/b.bin")
    with store.open("a.txt") as f:
        f.read()

    assert _snapshot(original) == before


def test_works_when_the_original_directory_is_not_writable(original: Path) -> None:
    """書き込み権限の無い原本でも動く = 書き込みを必要としない"""
    if os.geteuid() == 0:
        pytest.skip("root は権限を無視して書き込めるため、この検査は意味を持たない")
    paths = [original, original / "sub", original / "a.txt", original / "sub" / "b.bin"]
    modes = {p: p.stat().st_mode for p in paths}
    try:
        for p in paths:
            p.chmod(stat.S_IMODE(modes[p]) & ~0o222)
        store = OriginalStore(original)
        assert store.read_bytes("a.txt") == "あいう".encode()
        assert {e.path for e in store.list("sub")} == {"sub/b.bin"}
    finally:
        for p in paths:
            p.chmod(stat.S_IMODE(modes[p]))


def test_never_opens_a_file_for_writing(original: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """原本を書き込みの形で開く呼び出しがあれば失敗する"""
    opened: list[tuple[str, str]] = []
    real_open = builtins.open
    real_io_open = io.open
    real_os_open = os.open

    def spy_open(file, mode="r", *args, **kwargs):
        opened.append((str(file), mode))
        return real_open(file, mode, *args, **kwargs)

    def spy_io_open(file, mode="r", *args, **kwargs):
        opened.append((str(file), mode))
        return real_io_open(file, mode, *args, **kwargs)

    def spy_os_open(path, flags, *args, **kwargs):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
        opened.append((str(path), "w" if flags & write_flags else "r"))
        return real_os_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_io_open)
    monkeypatch.setattr(os, "open", spy_os_open)

    store = OriginalStore(original)
    store.read_bytes("a.txt")
    store.list("sub")
    with store.open("sub/b.bin") as f:
        f.read()

    inside = [(f, m) for f, m in opened if Path(f).resolve().is_relative_to(original.resolve())]
    assert inside, "原本の読み取りが観測されていない"
    assert all(not set(m) & set("wax+") for _, m in inside)


def test_handle_returned_by_open_cannot_write(original: Path) -> None:
    store = OriginalStore(original)
    with store.open("a.txt") as f, pytest.raises(io.UnsupportedOperation):
        f.write(b"x")
    assert (original / "a.txt").read_text(encoding="utf-8") == "あいう"


def test_exposes_no_operation_that_changes_the_original() -> None:
    """書き換えの操作があれば失敗する(公開されている名前の列挙に対する検査)"""
    forbidden = (
        "write",
        "delete",
        "remove",
        "unlink",
        "rename",
        "move",
        "replace",
        "mkdir",
        "rmdir",
        "touch",
        "chmod",
        "truncate",
        "save",
        "put",
        "create",
        "copy",
    )
    public = [n for n in dir(OriginalStore) if not n.startswith("_")]
    assert public, "公開の操作が無い"
    assert [n for n in public if any(w in n.lower() for w in forbidden)] == []


@pytest.mark.parametrize("path", ["../outside.txt", "sub/../../outside.txt", "/etc/hostname"])
def test_refuses_paths_outside_the_original_directory(original: Path, path: str) -> None:
    (original.parent / "outside.txt").write_text("外", encoding="utf-8")
    store = OriginalStore(original)
    with pytest.raises(OutsideOriginalError):
        store.read_bytes(path)


def test_refuses_symlink_that_escapes_the_original_directory(original: Path) -> None:
    (original.parent / "outside.txt").write_text("外", encoding="utf-8")
    (original / "link.txt").symlink_to(original.parent / "outside.txt")
    store = OriginalStore(original)
    with pytest.raises(OutsideOriginalError):
        store.read_bytes("link.txt")


def test_root_must_be_an_existing_directory(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        OriginalStore(tmp_path / "missing")

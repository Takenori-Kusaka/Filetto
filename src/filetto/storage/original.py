"""原本ディレクトリへの読み取り専用アクセス(F-001 受入基準1)。

原本を書き換える操作をこの層に置かない。削除・リネーム・移動・上書きは、原本の外に置く
ゴミ箱・操作履歴・版の保管(Task-2 以降)が担う。パスは原本ディレクトリからの相対パスで受け取り、
原本の外を指すもの(`..`、絶対パス、原本の外へ出るシンボリックリンク)は拒否する。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class OutsideOriginalError(ValueError):
    """指定されたパスが原本ディレクトリの外を指している"""


@dataclass(frozen=True)
class Entry:
    """原本ディレクトリの中の1項目。path は原本ディレクトリからの相対パス(区切りは /)"""

    path: str
    is_dir: bool
    size: int
    mtime_ns: int


class OriginalStore:
    """原本ディレクトリを読み取るだけの窓口"""

    def __init__(self, root: str | Path) -> None:
        resolved = Path(root).resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(f"原本ディレクトリが存在しない: {root}")
        self._root = resolved

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, rel: str) -> Path:
        if Path(rel).is_absolute():
            raise OutsideOriginalError(f"絶対パスは受け付けない: {rel}")
        target = (self._root / rel).resolve()
        if not target.is_relative_to(self._root):
            raise OutsideOriginalError(f"原本ディレクトリの外を指している: {rel}")
        return target

    def _entry(self, target: Path) -> Entry:
        st = target.stat()
        return Entry(
            path=target.relative_to(self._root).as_posix(),
            is_dir=target.is_dir(),
            size=st.st_size,
            mtime_ns=st.st_mtime_ns,
        )

    def list(self, rel: str = "") -> list[Entry]:
        """ディレクトリの直下の項目。原本の外へ出るシンボリックリンクは含めない"""
        directory = self._resolve(rel)
        entries = []
        for child in sorted(directory.iterdir()):
            resolved = child.resolve()
            if resolved.is_relative_to(self._root):
                entries.append(self._entry(child))
        return entries

    def stat(self, rel: str) -> Entry:
        return self._entry(self._resolve(rel))

    def open(self, rel: str) -> BinaryIO:
        """読み取り専用で開く。返した入出力への書き込みは io.UnsupportedOperation になる"""
        return self._resolve(rel).open("rb")

    def read_bytes(self, rel: str) -> bytes:
        with self.open(rel) as f:
            return f.read()

"""版の保管の窓口(F-001 受入基準17)。

他の層はこの型だけを使う。実装(Lore)の型・イベント・エラーをこの境界の外へ渡さない。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class VersionNotFoundError(LookupError):
    """指定されたパスに、指定された版が無い"""


@dataclass(frozen=True)
class Version:
    """1つの版。id は保管の実装が振る識別子。path は原本ディレクトリからの相対パス"""

    id: str
    path: str
    saved_at: datetime


class VersionStore(Protocol):
    def save(self, path: str, content: bytes) -> Version:
        """内容を新しい版として保管する"""
        ...

    def versions(self, path: str) -> list[Version]:
        """パスの版を古い順に返す。版が無ければ空"""
        ...

    def read(self, path: str, version_id: str) -> bytes:
        """版の内容を返す。無ければ VersionNotFoundError"""
        ...

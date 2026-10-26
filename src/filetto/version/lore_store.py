"""Lore を使う VersionStore(F-001 受入基準15・17)。

保管パスに Lore のリポジトリ(オフラインのローカル)を置き、版ごとに内容を書いてコミットする。
版の識別子はリビジョン番号。Lore の SDK(fluent API)は wait() を呼ぶまで何も実行しない(S0-005)
ため、呼び出しは必ず _run を通す。Lore の型・イベント・エラーはこのモジュールの外へ出さない。
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from lore import Lore, LoreError
from lore.types.args import (
    LoreFileHistoryArgs,
    LoreFileStageArgs,
    LoreFileWriteArgs,
    LoreGlobalArgs,
    LoreRepositoryCreateArgs,
    LoreRevisionCommitArgs,
)
from lore.types.enums import LoreEventTag

from filetto.version.store import Version, VersionNotFoundError


class LoreVersionStore:
    def __init__(self, store_path: str | Path) -> None:
        self._root = Path(store_path).resolve()
        self._globals = LoreGlobalArgs(repository_path=str(self._root), offline=True)
        if not (self._root / ".lore").exists():
            self._root.mkdir(parents=True, exist_ok=True)
            Lore.repository_create(
                self._globals, LoreRepositoryCreateArgs(repository_url="filetto")
            ).wait()

    def _events(self, call) -> list[tuple[str, dict]]:
        """呼び出しを実行し、イベントを素の値で集める(イベントのデータは呼び出しの後に破棄される)"""
        events: list[tuple[str, dict]] = []

        def collect(event, _context) -> None:
            tag = LoreEventTag(event.tag).name
            data = event.get_data()
            if tag in ("REVISION_COMMIT_REVISION", "FILE_HISTORY"):
                events.append((tag, {"number": str(data.revision_number)}))
            elif tag == "METADATA" and data.key == "timestamp":
                events.append((tag, {"ms": int(data.value.cdata.numeric)}))

        call.callback(collect).wait()
        return events

    def save(self, path: str, content: bytes) -> Version:
        target = self._root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        Lore.file_stage(self._globals, LoreFileStageArgs(paths=[str(target)])).wait()
        events = self._events(
            Lore.revision_commit(self._globals, LoreRevisionCommitArgs(message=path))
        )
        number = next(d["number"] for tag, d in events if tag == "REVISION_COMMIT_REVISION")
        stamp = next(d["ms"] for tag, d in events if tag == "METADATA")
        return Version(id=number, path=path, saved_at=_from_ms(stamp))

    def versions(self, path: str) -> list[Version]:
        if not (self._root / path).exists():
            return []
        args = LoreFileHistoryArgs(path=str(self._root / path))
        found: list[Version] = []
        number = None
        for tag, data in self._events(Lore.file_history(self._globals, args)):
            if tag == "FILE_HISTORY":
                number = data["number"]
            elif number is not None:
                found.append(Version(id=number, path=path, saved_at=_from_ms(data["ms"])))
                number = None
        # 履歴は新しい順に返るため、古い順へ並べ替える
        return sorted(found, key=lambda v: int(v.id))

    def read(self, path: str, version_id: str) -> bytes:
        if version_id not in {v.id for v in self.versions(path)}:
            raise VersionNotFoundError(f"版が無い: {path} @ {version_id}")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "content"
            args = LoreFileWriteArgs(
                path=str(self._root / path), revision=version_id, output=str(output)
            )
            try:
                Lore.file_write(self._globals, args).wait()
            except LoreError:
                raise VersionNotFoundError(f"版を読めない: {path} @ {version_id}") from None
            return output.read_bytes()


def _from_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, UTC)

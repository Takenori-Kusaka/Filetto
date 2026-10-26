"""REST API のアプリ(FastAPI)。

削除は物理削除ではなくゴミ箱への移動にする(F-001 受入基準2)。ハンドラは同期関数にして、
stdlib の sqlite3 とファイルの stat をスレッドプールで動かす(イベントループを塞がない)。
MCP サーバ(受入基準3)は同じゴミ箱を使い、同じ ASGI アプリの /mcp へマウントする。
WebUI は SvelteKit の静的出力を / へマウントし、データは /api/** から取る(ADR-0003)。
過去の版は VersionStore の背後から読む(受入基準16・17)。版は原本のパスで保管されている。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from filetto.history import HistoryStore, RelocateConflictError
from filetto.mcp import create_mcp
from filetto.storage import OriginalStore, OutsideOriginalError
from filetto.trash import (
    AlreadyTrashedError,
    NotTrashedError,
    RestoreConflictError,
    TrashEntry,
    TrashStore,
)
from filetto.version import Version, VersionNotFoundError, VersionStore


class TrashItem(BaseModel):
    path: str
    trashed_at: datetime
    # 完全削除までの残日数。無期限なら null(受入基準11)
    remaining_days: int | None

    @classmethod
    def of(cls, entry: TrashEntry, trash: TrashStore) -> TrashItem:
        return cls(
            path=entry.path,
            trashed_at=entry.trashed_at,
            remaining_days=trash.remaining_days(entry),
        )


class RenameRequest(BaseModel):
    name: str


class MoveRequest(BaseModel):
    # 移動先のディレクトリ(原本ディレクトリからの相対パス)
    to: str


class Relocated(BaseModel):
    path: str


class HistoryItem(BaseModel):
    at: datetime
    op: str
    before: str
    after: str | None
    via: str


class VersionItem(BaseModel):
    id: str
    path: str
    saved_at: datetime

    @classmethod
    def of(cls, version: Version) -> VersionItem:
        return cls(id=version.id, path=version.path, saved_at=version.saved_at)


class _SpaFiles(StaticFiles):
    """画面の経路(例: /trash)を直接開いたときも index.html を返す。/api/** は戻さない"""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code != 404 or path == "api" or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)


def create_app(
    original_root: str | Path,
    db_path: str | Path,
    web_dir: str | Path | None = None,
    versions: VersionStore | None = None,
) -> FastAPI:
    original = OriginalStore(original_root)
    trash = TrashStore(db_path, original)
    history = HistoryStore(db_path, original)
    mcp = create_mcp(trash, history)
    mcp_app = mcp.streamable_http_app(streamable_http_path="/")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # マウントした側の lifespan は動かないため、MCP のセッション管理をここで始める
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Filetto", lifespan=lifespan)
    app.state.mcp = mcp

    @app.delete("/api/files/{path:path}")
    def delete_file(path: str) -> TrashItem:
        """ファイルをゴミ箱へ移す。原本の実体は削除しない"""
        try:
            item = TrashItem.of(trash.trash(history.resolve(path)), trash)
            history.record_delete(path, "webui")
            return item
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="ファイルが見つからない") from e
        except OutsideOriginalError as e:
            raise HTTPException(status_code=400, detail="原本ディレクトリの外は扱わない") from e
        except AlreadyTrashedError as e:
            raise HTTPException(status_code=409, detail="既にゴミ箱に入っている") from e

    @app.get("/api/trash")
    def list_trash() -> list[TrashItem]:
        return [TrashItem.of(e, trash) for e in trash.list()]

    @app.post("/api/trash/{path:path}/restore")
    def restore_file(path: str) -> TrashItem:
        """ゴミ箱のファイルを削除前のパスへ戻す。同名の別ファイルがあれば 409 で、復元しない"""
        try:
            return TrashItem.of(trash.restore(path), trash)
        except NotTrashedError as e:
            raise HTTPException(status_code=404, detail="ゴミ箱に入っていない") from e
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="削除前のパスに実体が無い") from e
        except RestoreConflictError as e:
            raise HTTPException(status_code=409, detail="復元先に同名のファイルがある") from e

    def _relocate(move: Callable[[], str]) -> Relocated:
        try:
            return Relocated(path=move())
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="ファイルが見つからない") from e
        except RelocateConflictError as e:
            raise HTTPException(status_code=409, detail="移動先に同名のファイルがある") from e
        except (OutsideOriginalError, NotADirectoryError, ValueError) as e:
            # 名前に区切りを含む、移動先がディレクトリでない、原本の外を指す
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/api/files/{path:path}/rename")
    def rename_file(path: str, body: RenameRequest) -> Relocated:
        """名前を変える。原本の実体は変えず、変更前の名前を操作履歴へ残す"""
        return _relocate(lambda: history.rename(path, body.name, "webui"))

    @app.post("/api/files/{path:path}/move")
    def move_file(path: str, body: MoveRequest) -> Relocated:
        """別のディレクトリへ移す。原本の実体は動かさず、変更前のパスを操作履歴へ残す"""
        return _relocate(lambda: history.move(path, body.to, "webui"))

    @app.get("/api/history")
    def list_history() -> list[HistoryItem]:
        return [HistoryItem(**asdict(e)) for e in history.list()]

    def _original_path(path: str) -> str:
        try:
            return history.resolve(path)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="ファイルが見つからない") from e
        except OutsideOriginalError as e:
            raise HTTPException(status_code=400, detail="原本ディレクトリの外は扱わない") from e

    if versions is not None:

        @app.get("/api/files/{path:path}/versions")
        def list_versions(path: str) -> list[VersionItem]:
            """ファイルの過去の版を古い順に返す。リネーム・移動の後は、いまのパスで引く"""
            return [VersionItem.of(v) for v in versions.versions(_original_path(path))]

        @app.get("/api/files/{path:path}/versions/{version_id}")
        def read_version(path: str, version_id: str) -> Response:
            """指定した版の内容を返す(受入基準16)"""
            try:
                content = versions.read(_original_path(path), version_id)
            except VersionNotFoundError as e:
                raise HTTPException(status_code=404, detail="指定の版が無い") from e
            return Response(content, media_type="application/octet-stream")

    app.mount("/mcp", mcp_app)
    if web_dir is not None:
        # 経路の照合は登録順のため、/api/** と /mcp の後に置く
        app.mount("/", _SpaFiles(directory=web_dir, html=True), name="web")
    return app

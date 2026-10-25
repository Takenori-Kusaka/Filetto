"""REST API のアプリ(FastAPI)。

削除は物理削除ではなくゴミ箱への移動にする(F-001 受入基準2)。ハンドラは同期関数にして、
stdlib の sqlite3 とファイルの stat をスレッドプールで動かす(イベントループを塞がない)。
MCP サーバ(受入基準3)は同じゴミ箱を使い、同じ ASGI アプリの /mcp へマウントする。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from filetto.mcp import create_mcp
from filetto.storage import OriginalStore, OutsideOriginalError
from filetto.trash import (
    AlreadyTrashedError,
    NotTrashedError,
    RestoreConflictError,
    TrashEntry,
    TrashStore,
)


class TrashItem(BaseModel):
    path: str
    trashed_at: datetime

    @classmethod
    def of(cls, entry: TrashEntry) -> TrashItem:
        return cls(path=entry.path, trashed_at=entry.trashed_at)


def create_app(original_root: str | Path, db_path: str | Path) -> FastAPI:
    trash = TrashStore(db_path, OriginalStore(original_root))
    mcp = create_mcp(trash)
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
            return TrashItem.of(trash.trash(path))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="ファイルが見つからない") from e
        except OutsideOriginalError as e:
            raise HTTPException(status_code=400, detail="原本ディレクトリの外は扱わない") from e
        except AlreadyTrashedError as e:
            raise HTTPException(status_code=409, detail="既にゴミ箱に入っている") from e

    @app.get("/api/trash")
    def list_trash() -> list[TrashItem]:
        return [TrashItem.of(e) for e in trash.list()]

    @app.post("/api/trash/{path:path}/restore")
    def restore_file(path: str) -> TrashItem:
        """ゴミ箱のファイルを削除前のパスへ戻す。同名の別ファイルがあれば 409 で、復元しない"""
        try:
            return TrashItem.of(trash.restore(path))
        except NotTrashedError as e:
            raise HTTPException(status_code=404, detail="ゴミ箱に入っていない") from e
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="削除前のパスに実体が無い") from e
        except RestoreConflictError as e:
            raise HTTPException(status_code=409, detail="復元先に同名のファイルがある") from e

    app.mount("/mcp", mcp_app)
    return app

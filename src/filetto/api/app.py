"""REST API のアプリ(FastAPI)。

削除は物理削除ではなくゴミ箱への移動にする(F-001 受入基準2)。ハンドラは同期関数にして、
stdlib の sqlite3 とファイルの stat をスレッドプールで動かす(イベントループを塞がない)。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from filetto.storage import OriginalStore, OutsideOriginalError
from filetto.trash import AlreadyTrashedError, TrashEntry, TrashStore


class TrashItem(BaseModel):
    path: str
    trashed_at: datetime

    @classmethod
    def of(cls, entry: TrashEntry) -> TrashItem:
        return cls(path=entry.path, trashed_at=entry.trashed_at)


def create_app(original_root: str | Path, db_path: str | Path) -> FastAPI:
    trash = TrashStore(db_path, OriginalStore(original_root))
    app = FastAPI(title="Filetto")

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

    return app

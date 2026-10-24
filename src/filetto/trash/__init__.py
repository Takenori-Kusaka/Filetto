"""ゴミ箱。削除は原本を消さずにゴミ箱へ入れる論理削除にする(F-001 受入基準2)。"""

from filetto.trash.store import AlreadyTrashedError, TrashEntry, TrashStore

__all__ = ["AlreadyTrashedError", "TrashEntry", "TrashStore"]

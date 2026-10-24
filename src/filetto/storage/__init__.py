"""原本ディレクトリへのアクセス層。原本は読み取りだけを行う(F-001 受入基準1)。"""

from filetto.storage.original import Entry, OriginalStore, OutsideOriginalError

__all__ = ["Entry", "OriginalStore", "OutsideOriginalError"]

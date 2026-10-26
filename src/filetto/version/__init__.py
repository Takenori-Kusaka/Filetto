"""版の保管(F-001 受入基準15〜22)。Lore は VersionStore の背後だけで使う(受入基準17)。"""

from filetto.version.store import Version, VersionNotFoundError, VersionStore
from filetto.version.watcher import OverwriteWatcher

__all__ = [
    "OverwriteWatcher",
    "Version",
    "VersionNotFoundError",
    "VersionStore",
]

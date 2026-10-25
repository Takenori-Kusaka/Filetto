"""設定の読み取り。値は環境変数から読み、既定値は defaults.toml に置く。"""

from filetto.config.retention import RETENTION_ENV, UNLIMITED, load_retention

__all__ = ["RETENTION_ENV", "UNLIMITED", "load_retention"]

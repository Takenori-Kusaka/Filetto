"""ゴミ箱の保持期間(F-001 受入基準8・9・10)。

環境変数の値は正の整数(日)か UNLIMITED。未設定なら defaults.toml の既定値を使う。
無期限は None で表す(保持期間が無い)。
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from datetime import timedelta
from importlib.resources import files

RETENTION_ENV = "FILETTO_TRASH_RETENTION_DAYS"
UNLIMITED = "unlimited"


def _default() -> str:
    data = tomllib.loads(files("filetto.config").joinpath("defaults.toml").read_text("utf-8"))
    return str(data["trash_retention_days"])


def load_retention(env: Mapping[str, str] | None = None) -> timedelta | None:
    """保持期間を返す。無期限なら None。不正な値は ValueError"""
    env = os.environ if env is None else env
    raw = env.get(RETENTION_ENV)
    value = (_default() if raw is None else raw).strip()
    if value == UNLIMITED:
        return None
    if not value.isdigit() or int(value) <= 0:
        raise ValueError(f"{RETENTION_ENV} は正の整数(日)か {UNLIMITED!r}: {raw!r}")
    return timedelta(days=int(value))

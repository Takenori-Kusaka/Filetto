"""Lore の保管パス(F-001 受入基準18・19)。

保管パスは環境変数から読む。既定値は持たない(Lore の既定は一時ディレクトリで、消えるため。S0-005)。
未設定のまま起動したら、設定の不足を標準エラー出力へ書いて起動を止める。
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TextIO

LORE_STORE_ENV = "FILETTO_LORE_STORE_PATH"


def require_lore_store_path(
    env: Mapping[str, str] | None = None, stderr: TextIO | None = None
) -> Path:
    """保管パスを返す。未設定なら標準エラー出力へ書き、SystemExit で起動を止める"""
    env = os.environ if env is None else env
    raw = env.get(LORE_STORE_ENV, "").strip()
    if not raw:
        print(
            f"設定が不足しています: {LORE_STORE_ENV}(Lore の保管パス)が設定されていません",
            file=stderr or sys.stderr,
        )
        raise SystemExit(2)
    return Path(raw)

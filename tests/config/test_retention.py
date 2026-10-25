"""F-001 受入基準8・9・10 の検査(保持期間の設定)。

受入基準8: システムは保持期間を環境変数から読み取り、既定値を 30 日としなければならない。
受入基準9: システムは保持期間の設定として無期限を受け付けなければならない。
受入基準10: システムは保持期間をソースコード内の定数として持ってはならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import re
from datetime import timedelta
from pathlib import Path

import pytest
from filetto.config import RETENTION_ENV, load_retention

SRC = Path(__file__).resolve().parents[2] / "src" / "filetto"


def test_default_retention_is_30_days() -> None:
    assert load_retention({}) == timedelta(days=30)


def test_retention_is_read_from_the_environment() -> None:
    assert load_retention({RETENTION_ENV: "7"}) == timedelta(days=7)
    assert load_retention({RETENTION_ENV: " 90 "}) == timedelta(days=90)


def test_unlimited_retention_is_accepted() -> None:
    assert load_retention({RETENTION_ENV: "unlimited"}) is None


@pytest.mark.parametrize("value", ["", "abc", "0", "-1", "1.5", "30d"])
def test_invalid_retention_is_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        load_retention({RETENTION_ENV: value})


def test_retention_env_is_named_for_the_trash() -> None:
    assert RETENTION_ENV.startswith("FILETTO_")


def test_retention_is_not_a_constant_in_the_source() -> None:
    """既定の 30 日を、Python のソースに数値として書かない"""
    hits = [
        f"{p.relative_to(SRC)}:{n}"
        for p in SRC.rglob("*.py")
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"(?<![\w.])30(?![\w.])", line.split("#")[0])
    ]
    assert hits == []

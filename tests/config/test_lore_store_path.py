"""F-001 受入基準18・19 の検査(Lore の保管パスの設定)。

受入基準18: システムは Lore の保管パスを環境変数から読み取らなければならない。
受入基準19: Lore の保管パスが設定されていない状態で起動した場合、システムは起動を中止し、
設定が不足していることを標準エラー出力へ記録しなければならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import io
from pathlib import Path

import pytest

from filetto.config import LORE_STORE_ENV, require_lore_store_path


def test_store_path_is_read_from_the_environment(tmp_path: Path) -> None:
    assert require_lore_store_path({LORE_STORE_ENV: str(tmp_path)}) == tmp_path


@pytest.mark.parametrize("env", [{}, {LORE_STORE_ENV: ""}, {LORE_STORE_ENV: "   "}])
def test_missing_store_path_stops_startup_and_reports_to_stderr(env: dict[str, str]) -> None:
    stderr = io.StringIO()
    with pytest.raises(SystemExit) as stopped:
        require_lore_store_path(env, stderr=stderr)
    assert stopped.value.code != 0
    assert LORE_STORE_ENV in stderr.getvalue()

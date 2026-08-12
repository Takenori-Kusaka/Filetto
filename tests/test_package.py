"""パッケージが読み込める状態にあることを検査する。

機能の検査ではありません。ADR-0006 で確定した実装スタックが
CI 上で成立していることを確かめるためのものです。
"""

import filetto


def test_version_is_exposed() -> None:
    assert filetto.__version__ == "0.0.0"


def test_public_names() -> None:
    assert filetto.__all__ == ["__version__"]

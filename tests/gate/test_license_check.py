"""ライセンス検査の判定(scripts/gate/license-check.mjs)を CI の test 工程で走らせる。

G-5 の test 工程は pytest を呼びます。判定の本体は Node で書かれているため、
ここから `node --test` を起動して CI の中へ引き込みます。この橋渡しが無いと、
テストがリポジトリに存在するのに一度も実行されない状態になります。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = ROOT / "tests" / "gate" / "license-check.test.mjs"
TARGET = ROOT / "scripts" / "gate" / "license-check.mjs"


def test_license_check_target_exists() -> None:
    """判定スクリプトが存在すること。存在しないまま通る経路を作らない。"""
    assert TARGET.is_file(), f"{TARGET} がありません"


def test_license_check_node_suite() -> None:
    """node --test の結果をそのまま合否にする。"""
    node = shutil.which("node")
    if node is None:
        pytest.fail(
            "node が見つかりません。ライセンス検査の判定は Node で実装されており、"
            "実行できない場合は検査を実施していない状態になります"
        )

    result = subprocess.run(  # noqa: S603
        [node, "--test", str(TEST_FILE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

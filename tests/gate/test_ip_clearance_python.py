"""ip-clearance-python.mjs の照合を検証する。

括弧つきの別名を含む1語の表記は通し、複合式(AND)の許可されないライセンスは落とすことを確かめる。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gate" / "ip-clearance-python.mjs"


def run(license_text: str) -> int:
    packages = [{"Name": "pkg", "Version": "1", "License": license_text}]
    env = {**os.environ, "PIT_IN_ALLOWED_LICENSES": "MIT;MPL-2.0"}
    result = subprocess.run(
        ["node", str(SCRIPT)],
        input=json.dumps(packages),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    return result.returncode


def test_paren_alias_of_allowed_license_passes() -> None:
    assert run("Mozilla Public License 2.0 (MPL 2.0)") == 0


def test_or_expression_passes_when_one_side_allowed() -> None:
    assert run("MIT OR GPL-3.0-only") == 0


def test_and_expression_fails_when_one_side_not_allowed() -> None:
    assert run("MIT AND GPL-3.0-only") == 1


def test_single_disallowed_license_fails() -> None:
    assert run("GPL-3.0-only") == 1

"""カバレッジ判定(scripts/gate/coverage-check.mjs)を検証する。

**測定対象が小さすぎる間、閾値は品質について何も述べません。** 2026-08-14 の
実測では statements が 2 で 100% でした。**「通過した」と「判定していない」を
区別できる形にします。**
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/coverage-check.mjs"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", work / "scripts")
    shutil.copytree(ROOT / "adapters", work / "adapters")
    shutil.copy(ROOT / "process.config.json", work / "process.config.json")
    return work


def _coverage(work: Path, pct: float, statements: int) -> None:
    body = {"totals": {"percent_covered": pct, "num_statements": statements}}
    (work / "coverage.json").write_text(json.dumps(body), encoding="utf-8")


def _run(work: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [_node(), SCRIPT],
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _min_statements(work: Path) -> int:
    return json.loads((work / "process.config.json").read_text(encoding="utf-8"))["ci"][
        "coverageMinStatements"
    ]


def test_測定対象が下限未満なら判定を実施しない(repo: Path) -> None:
    _coverage(repo, 100.0, _min_statements(repo) - 1)
    r = _run(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "判定を実施しません" in r.stdout + r.stderr


def test_実施しなかったことを証跡へ残す(repo: Path) -> None:
    """「通過した」と「判定していない」を区別できる形にする。"""
    _coverage(repo, 100.0, 2)
    _run(repo)
    result = json.loads((repo / "evidence/coverage-result.json").read_text(encoding="utf-8"))
    assert result["measured"] is False
    assert result["statements"] == 2


def test_測定対象が下限以上なら判定する(repo: Path) -> None:
    _coverage(repo, 95.0, _min_statements(repo) + 10)
    r = _run(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    result = json.loads((repo / "evidence/coverage-result.json").read_text(encoding="utf-8"))
    assert result["measured"] is True


def test_否定_下限以上で閾値を下回れば落ちる(repo: Path) -> None:
    """実施しない仕組みが、本来落とすべきものまで通していないこと。"""
    _coverage(repo, 10.0, _min_statements(repo) + 10)
    r = _run(repo)
    assert r.returncode == 1
    assert "下回っています" in r.stdout + r.stderr


def test_設定が測定対象の下限を持つ() -> None:
    c = json.loads((ROOT / "process.config.json").read_text(encoding="utf-8"))
    assert c["ci"]["coverageMinStatements"] > 0

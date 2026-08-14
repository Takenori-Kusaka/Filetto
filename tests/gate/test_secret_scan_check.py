"""秘匿情報の検査の判定部(scripts/gate/secret-scan-check.mjs)を検証する。

**標準は本基準を「台帳記録による通過を認めない唯一の基準」としています。**
それにもかかわらず `secretScan` が空のまま「実施しません」で通過していました。

**空の入力を合格にしないこと**を、否定側で確かめます。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/secret-scan-check.mjs"
POLICY = ROOT / "scripts/gate/secret-scan-policy.json"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


def _run(stdin: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [_node(), SCRIPT],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _report(results: dict) -> str:
    return json.dumps({"version": "1.5.0", "plugins_used": [{"name": "x"}], "results": results})


def test_検出0件なら通り件数を出力する() -> None:
    r = _run(_report({}))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "秘匿情報の疑い: 0 件" in r.stdout


def test_否定_検出があれば落ちる() -> None:
    results = {"src/a.py": [{"type": "AWS Access Key", "line_number": 3}]}
    r = _run(_report(results))
    assert r.returncode == 1
    assert "src/a.py:3" in r.stdout + r.stderr


def test_否定_入力が空なら落ちる() -> None:
    """道具が動かなかったことを合格として記録しない。"""
    r = _run("")
    assert r.returncode == 1
    assert "空の入力を合格として記録しません" in r.stdout + r.stderr


def test_否定_JSONでなければ落ちる() -> None:
    r = _run("not json")
    assert r.returncode == 1


def test_否定_resultsが無ければ落ちる() -> None:
    r = _run(json.dumps({"version": "1.5.0"}))
    assert r.returncode == 1
    assert "results" in r.stdout + r.stderr


def test_理由を添えた除外は通り理由が出力される(tmp_path: Path) -> None:
    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", work / "scripts")
    pol = work / "scripts/gate/secret-scan-policy.json"
    p = json.loads(pol.read_text(encoding="utf-8"))
    p["allowed"] = [{"path": "docs/sample.md", "reason": "検査の説明に書いた例"}]
    pol.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")

    results = {"docs/sample.md": [{"type": "Hex High Entropy String", "line_number": 1}]}
    r = _run(_report(results), cwd=work)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "検査の説明に書いた例" in r.stdout


def test_除外が0件でも件数を出力する() -> None:
    r = _run(_report({}))
    assert "理由を添えて除外したもの: 0 件" in r.stdout


def test_アダプタが空でないこと() -> None:
    """空のままだと adapter.mjs が「実施しません」で通す。"""
    adapter = json.loads((ROOT / "adapters/python.json").read_text(encoding="utf-8"))
    cmd = adapter["commands"]["secretScan"]
    assert cmd.strip()
    assert "secret-scan-check.mjs" in cmd


def test_方針が理由と除外の扱いを書いている() -> None:
    p = json.loads(POLICY.read_text(encoding="utf-8"))
    assert p["why"].strip()
    assert p["excludeFiles"].strip()
    assert isinstance(p["allowed"], list)

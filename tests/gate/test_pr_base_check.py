"""PR のマージ先の検査(scripts/gate/pr-base-check.mjs)を検証する。

検査そのものを検査します。**通ってはならないものが通らないこと**を否定側で確かめます。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/pr-base-check.mjs"
POLICY = ROOT / "scripts/gate/pr-base-policy.json"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


def _run(*argv: str, body: str | None = None, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    env = {"PR_BODY": body} if body is not None else None
    return subprocess.run(  # noqa: S603
        [_node(), SCRIPT, *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**_base_env(), **(env or {})},
        check=False,
    )


def _base_env() -> dict[str, str]:
    import os

    e = dict(os.environ)
    e.pop("PR_BODY", None)
    e.pop("GITHUB_BASE_REF", None)
    return e


def _policy() -> dict:
    return json.loads(POLICY.read_text(encoding="utf-8"))


def test_方針が既定ブランチと記載の目印を持つ() -> None:
    p = _policy()
    assert p["defaultBase"]
    assert p["justificationMarker"]


def test_既定ブランチ宛なら通り_その事実を出力する() -> None:
    base = _policy()["defaultBase"]
    r = _run("--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"この PR のマージ先: {base}" in r.stdout


def test_否定_既定ブランチ以外で理由が無ければ落ちる() -> None:
    r = _run("--base", "docs/parent-pr", body="理由を書いていない本文")
    assert r.returncode == 1
    assert _policy()["justificationMarker"] in r.stdout + r.stderr


def test_理由を書けば通り_理由を出力する() -> None:
    marker = _policy()["justificationMarker"]
    reason = "親 PR #10 の ADR に依存するため"
    r = _run("--base", "docs/parent-pr", body=f"本文\n{marker} {reason}\n続き")
    assert r.returncode == 0, r.stdout + r.stderr
    assert reason in r.stdout


def test_否定_目印だけで理由が空なら落ちる() -> None:
    marker = _policy()["justificationMarker"]
    r = _run("--base", "docs/parent-pr", body=f"本文\n{marker}\n続き")
    assert r.returncode == 1


def test_否定_マージ先を特定できなければ落ちる() -> None:
    """特定できないまま通す経路を作らない。"""
    r = _run(body="本文")
    assert r.returncode == 1
    assert "特定できません" in r.stdout + r.stderr


def test_否定_方針が無ければ落ちる(tmp_path: Path) -> None:
    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts/gate", work / "scripts/gate")
    (work / "scripts/gate/pr-base-policy.json").unlink()
    r = _run("--base", "main", body="", cwd=work)
    assert r.returncode == 1
    assert "pr-base-policy.json" in r.stdout + r.stderr

def test_本文の出所を必ず出力する() -> None:
    """イベントの値を読んだのか、API から読み直したのかが記録に残らないと、
    「理由を書いたのに落ちる」が起きたときに原因を切り分けられない(#119)。"""
    r = _run("--base", "main", body="")
    assert "本文の出所:" in r.stdout


def test_PR番号が無ければイベントの値を使う() -> None:
    marker = _policy()["justificationMarker"]
    r = _run("--base", "docs/parent-pr", body=f"{marker} 親に依存するため")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "イベントのペイロード" in r.stdout


def test_APIを引けないときはイベントの値へ落ちる(tmp_path: Path) -> None:
    """API が引けないことを理由に、検査を実施しない経路を作らない。"""
    import os

    marker = _policy()["justificationMarker"]
    env = {**_base_env(), "PR_BODY": f"{marker} 親に依存するため", "PATH": str(tmp_path)}
    r = subprocess.run(  # noqa: S603
        [_node(), SCRIPT, "--base", "docs/parent-pr", "--pr", "999999"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**env, "SystemRoot": os.environ.get("SystemRoot", "")},
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "取り直せませんでした" in r.stdout


def test_失敗のときに再実行の手順を出す() -> None:
    """本文を編集しただけでは CI が起動しないことを、落ちた本人へ伝える(#119)。"""
    r = _run("--base", "docs/parent-pr", body="理由を書いていない本文")
    assert r.returncode == 1
    out = r.stdout + r.stderr
    assert "gh run rerun" in out
    assert "edited" in out

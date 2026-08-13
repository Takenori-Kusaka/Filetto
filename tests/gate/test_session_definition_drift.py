"""ロール定義の乖離検査(scripts/gate/session-definition-drift.mjs)を検証する。

検査そのものを検査します。**通ってはならないものが通らないこと**を否定側で確かめます。
検査が通ることと、検査が働いていることは別だからです。

リポジトリを一時ディレクトリへ写して壊し、検査が落ちることを確認します。
本物のリポジトリは書き換えません。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/session-definition-drift.mjs"
MAP = "scripts/gate/session-definition-map.json"
SOURCE = ".claude/skills/dev/SKILL.md"
GENERATED = ".gemini/commands/dev.toml"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail(
            "node が見つかりません。乖離検査は Node で実装されており、"
            "実行できない場合は検査を実施していない状態になります"
        )
    return node


def _run(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [_node(), SCRIPT],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """検査に要るファイルだけを写した作業場を作る。"""
    work = tmp_path / "repo"
    for rel in ("scripts/gate", ".claude/skills", ".claude/agents", ".gemini/commands"):
        src = ROOT / rel
        if src.exists():
            shutil.copytree(src, work / rel)
    return work


def test_現状は乖離が無い() -> None:
    r = _run(ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 組で乖離を検出" in r.stdout


def test_許容した差分を必ず出力する() -> None:
    r = _run(ROOT)
    assert "許容した差分:" in r.stdout
    assert "理由:" in r.stdout


def test_未展開のロール定義を数え上げる() -> None:
    r = _run(ROOT)
    assert "未展開のロール定義:" in r.stdout


def test_否定_生成物を書き換えると落ちる(sandbox: Path) -> None:
    target = sandbox / GENERATED
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "**このレーンの成果物は「実装と単体テスト」です。**",
            "**このレーンの成果物は何でもよいです。**",
        ),
        encoding="utf-8",
    )
    r = _run(sandbox)
    assert r.returncode == 1
    assert "乖離" in r.stdout + r.stderr


def test_否定_正本に追記すると落ちる(sandbox: Path) -> None:
    target = sandbox / SOURCE
    target.write_text(target.read_text(encoding="utf-8") + "\n\n追記された行\n", encoding="utf-8")
    r = _run(sandbox)
    assert r.returncode == 1


def test_否定_生成物が無いと落ちる(sandbox: Path) -> None:
    (sandbox / GENERATED).unlink()
    r = _run(sandbox)
    assert r.returncode == 1
    assert "がありません" in r.stdout + r.stderr


def test_否定_許容差分が古くなると落ちる(sandbox: Path) -> None:
    """生成物から許容差分の文言が消えたら、map が古い証拠として落とす。"""
    mapping = json.loads((sandbox / MAP).read_text(encoding="utf-8"))
    mapping["pairs"][0]["allowedDifferences"][0]["generated"] = "存在しない文言"
    (sandbox / MAP).write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    r = _run(sandbox)
    assert r.returncode == 1
    assert "allowedDifferences" in r.stdout + r.stderr


def test_否定_対応が0件なら落ちる(sandbox: Path) -> None:
    """対象0件を「実施した」として通す経路を作らない。"""
    mapping = json.loads((sandbox / MAP).read_text(encoding="utf-8"))
    mapping["pairs"] = []
    (sandbox / MAP).write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    r = _run(sandbox)
    assert r.returncode == 1


def test_否定_ロール定義が消えると落ちる(sandbox: Path) -> None:
    (sandbox / ".claude/skills/platform/SKILL.md").unlink()
    r = _run(sandbox)
    assert r.returncode == 1
    assert "roleDefinitions" in r.stdout + r.stderr


def test_許容差分そのものは乖離としない(sandbox: Path) -> None:
    """ランタイム差の2件は、書かれているとおりであれば通る。"""
    r = _run(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "許容した差分: 2 件" in r.stdout

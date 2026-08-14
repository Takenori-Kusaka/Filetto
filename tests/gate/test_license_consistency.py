"""ライセンス宣言の整合検査(scripts/gate/license-consistency.mjs)を検証する。

**README が「コードは MIT」と書き、LICENSE と pyproject.toml が AGPL だった**
という事例が起点です(#112)。公開後に回収が難しい種類の誤りのため、
**食い違いを見逃さないこと**を否定側で確かめます。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/license-consistency.mjs"
CONFIG = ROOT / "scripts/gate/license-declaration.json"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


def _run(cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
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
def repo(tmp_path: Path) -> Path:
    """検査に要るファイルだけを写した作業場。本物は書き換えない。"""
    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", work / "scripts")
    for f in ("README.md", "LICENSE", "LICENSE-docs", "pyproject.toml"):
        shutil.copy(ROOT / f, work / f)
    return work


def test_現状は食い違いが無い() -> None:
    r = _run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 件の食い違いを検出" in r.stdout


def test_突き合わせた宣言をすべて出力する() -> None:
    r = _run()
    assert "pyproject.toml" in r.stdout
    assert "README.md" in r.stdout
    assert "LICENSE" in r.stdout
    assert "LICENSE-docs" in r.stdout


def test_否定_READMEが別のライセンスを書いていたら落ちる(repo: Path) -> None:
    """本件の事例そのもの。README だけ MIT のまま残る。"""
    p = repo / "README.md"
    p.write_text(
        p.read_text(encoding="utf-8").replace(
            "code=AGPL-3.0-or-later", "code=MIT"
        ),
        encoding="utf-8",
    )
    r = _run(repo)
    assert r.returncode == 1
    assert "食い違って" in r.stdout + r.stderr


def test_否定_READMEに宣言が無ければ落ちる(repo: Path) -> None:
    """文章から推測しません。推測では取りこぼしを検出できません。"""
    p = repo / "README.md"
    body = p.read_text(encoding="utf-8")
    start = body.index("<!-- license:")
    end = body.index("-->", start) + 3
    p.write_text(body[:start] + body[end:], encoding="utf-8")
    r = _run(repo)
    assert r.returncode == 1
    assert "機械可読なライセンス宣言がありません" in r.stdout + r.stderr


def test_否定_LICENSE全文が別のものなら落ちる(repo: Path) -> None:
    """識別子だけ直して全文を差し替え忘れた場合。"""
    mit = "MIT License\n\nPermission is hereby granted...\n"
    (repo / "LICENSE").write_text(mit, encoding="utf-8")
    r = _run(repo)
    assert r.returncode == 1
    assert "全文ではありません" in r.stdout + r.stderr


def test_否定_正本を読めなければ落ちる(repo: Path) -> None:
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    r = _run(repo)
    assert r.returncode == 1
    assert "license を読み取れません" in r.stdout + r.stderr


def test_否定_LICENSEが無ければ落ちる(repo: Path) -> None:
    (repo / "LICENSE").unlink()
    r = _run(repo)
    assert r.returncode == 1


def test_否定_設定が無ければ落ちる(repo: Path) -> None:
    (repo / "scripts/gate/license-declaration.json").unlink()
    r = _run(repo)
    assert r.returncode == 1
    assert "license-declaration.json" in r.stdout + r.stderr


def test_設定が正本と見出しの対応を持つ() -> None:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert c["sourceOfTruth"]["file"] == "pyproject.toml"
    assert "AGPL-3.0-or-later" in c["titles"]
    assert "CC-BY-4.0" in c["titles"]

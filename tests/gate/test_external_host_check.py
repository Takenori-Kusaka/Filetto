"""組織外ホストへの参照の検査(scripts/gate/external-host-check.mjs)を検証する。

**2026-08-14、着手決裁の資料を claude.ai へ置いた**(#115)。組織が保存期間も
アクセス権も制御できないホストに、決裁の入力が置かれた状態になった。

**この検査が見つけるのは、リポジトリに残った参照だけです。** 発行そのものは
検出できません。その限界が出力に残ることも確かめます。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/external-host-check.mjs"
CONFIG = ROOT / "scripts/gate/external-hosts.json"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


def _run(target: Path, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [_node(), SCRIPT, str(target)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    return d


def test_現状は参照が無い() -> None:
    r = subprocess.run(  # noqa: S603
        [_node(), SCRIPT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "組織の管理外のホストへの参照: 0 件" in r.stdout


def test_否定_claude_ai_への参照は落ちる(docs: Path) -> None:
    """本件の事例そのもの。"""
    url = "https://claude.ai/code/artifact/582d8408-0308-4c05-b4f2-9ec433532e90"
    (docs / "gate.md").write_text(f"決裁資料: {url}\n", encoding="utf-8")
    r = _run(docs)
    assert r.returncode == 1
    assert "claude.ai" in r.stdout + r.stderr


def test_否定_他の組織外ホストも落ちる(docs: Path) -> None:
    (docs / "a.md").write_text("資料: https://docs.google.com/document/d/xxx\n", encoding="utf-8")
    r = _run(docs)
    assert r.returncode == 1


def test_理由を添えれば除外される(docs: Path) -> None:
    """事故の記録として URL を書く場面がある。理由の記載を求める。"""
    body = (
        "発行した URL: https://claude.ai/code/artifact/xxx"
        " <!-- external-host-ok: 事故の記録 -->\n"
    )
    (docs / "a.md").write_text(body, encoding="utf-8")
    r = _run(docs)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "理由を添えて除外した行: 1 件" in r.stdout
    assert "事故の記録" in r.stdout


def test_否定_理由の無い注記では除外されない(docs: Path) -> None:
    body = "URL: https://claude.ai/x <!-- external-host-ok -->\n"
    (docs / "a.md").write_text(body, encoding="utf-8")
    r = _run(docs)
    assert r.returncode == 1


def test_0件でも件数を出力する(docs: Path) -> None:
    (docs / "a.md").write_text("本文\n", encoding="utf-8")
    r = _run(docs)
    assert "組織の管理外のホストへの参照: 0 件" in r.stdout
    assert "理由を添えて除外した行: 0 件" in r.stdout


def test_検査の限界を毎回出力する(docs: Path) -> None:
    """「検査が通ったから外部へ出していない」と読まれないようにする。"""
    (docs / "a.md").write_text("本文\n", encoding="utf-8")
    r = _run(docs)
    assert "発行そのものは検出できません" in r.stdout


def test_否定_ホスト一覧が空なら落ちる(tmp_path: Path) -> None:
    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", work / "scripts")
    cfg = work / "scripts/gate/external-hosts.json"
    c = json.loads(cfg.read_text(encoding="utf-8"))
    c["deniedHosts"] = []
    cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    (work / "docs").mkdir()
    (work / "docs/a.md").write_text("本文\n", encoding="utf-8")
    r = _run(work / "docs", cwd=work)
    assert r.returncode == 1
    assert "deniedHosts" in r.stdout + r.stderr


def test_設定が理由と限界を書いている() -> None:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert c["why"].strip()
    assert c["limitationNote"].strip()
    assert "claude.ai" in c["deniedHosts"]

"""マージ済み PR の到達検査(scripts/gate/merged-reachability.mjs)を検証する。

PR の一覧は `--pr-json` で与えます。gh とネットワークに依存させないためです。
祖先判定は本物の git を使います。判定の中核を模擬に置き換えると、検査を検査した
ことになりません。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/merged-reachability.mjs"
POLICY = ROOT / "scripts/gate/pr-base-policy.json"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


def _git(*argv: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *argv], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


# 判定の基準を HEAD に差し替えます。CI の checkout は fetch-depth: 1 で
# origin/main を持たないため、既定ブランチに依存すると環境しだいで落ちます。
# 確かめたいのは「祖先か否か」であって、基準がどのブランチかではありません。
BASE_REF = "HEAD"


@pytest.fixture
def reached_sha() -> str:
    """基準そのもの。必ず祖先である。"""
    return _git("rev-parse", f"{BASE_REF}^{{commit}}")


@pytest.fixture
def unreached_sha() -> str:
    """どこからも参照されない孤立コミット。祖先になり得ない。"""
    tree = _git("rev-parse", f"{BASE_REF}^{{tree}}")
    return subprocess.run(  # noqa: S603
        ["git", "commit-tree", tree, "-m", "test: 到達していないコミット"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=_commit_env(),
    ).stdout.strip()


def _commit_env() -> dict[str, str]:
    import os

    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }


def _pr(number: int, sha: str | None, base: str = "main") -> dict:
    return {
        "number": number,
        "title": f"テスト PR {number}",
        "baseRefName": base,
        "headRefName": f"test/{number}",
        "mergedAt": "2026-08-13T00:00:00Z",
        "mergeCommit": {"oid": sha} if sha else None,
    }


def _run(tmp_path: Path, prs: list[dict], *argv: str) -> subprocess.CompletedProcess[str]:
    f = tmp_path / "prs.json"
    f.write_text(json.dumps(prs, ensure_ascii=False), encoding="utf-8")
    return subprocess.run(  # noqa: S603
        [_node(), SCRIPT, "--pr-json", str(f), "--base-ref", BASE_REF, "--no-fetch", *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_到達しているPRは通る(tmp_path: Path, reached_sha: str) -> None:
    r = _run(tmp_path, [_pr(1, reached_sha)])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "到達している: 1 件" in r.stdout
    assert "到達していない PR: 0 件" in r.stdout


def test_否定_到達していないPRは落ちる(tmp_path: Path, unreached_sha: str) -> None:
    r = _run(tmp_path, [_pr(9001, unreached_sha, base="docs/parent")])
    assert r.returncode == 1
    assert "到達していない PR: 1 件" in r.stdout
    assert "#9001" in r.stdout + r.stderr


def test_否定_マージコミットが無いものは判定不能として落ちる(tmp_path: Path) -> None:
    """判定できないものを通す経路を作らない。"""
    r = _run(tmp_path, [_pr(9002, None)])
    assert r.returncode == 1
    assert "到達を判定できなかった PR: 1 件" in r.stdout


def test_否定_手元に無いコミットは判定不能として落ちる(tmp_path: Path) -> None:
    r = _run(tmp_path, [_pr(9003, "0" * 40)])
    assert r.returncode == 1
    assert "到達を判定できなかった PR: 1 件" in r.stdout


def test_マージ先が既定ブランチでないPRを数え上げる(tmp_path: Path, reached_sha: str) -> None:
    r = _run(tmp_path, [_pr(1, reached_sha, base="docs/parent")])
    assert "マージ先が main でない PR: 1 件" in r.stdout


def test_0件でも件数を出力する(tmp_path: Path) -> None:
    r = _run(tmp_path, [])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "検査したマージ済み PR: 0 件" in r.stdout
    assert "到達していない PR: 0 件" in r.stdout


def test_方針のresolvedが形を満たす() -> None:
    """別経路で到達済みとする例外は、理由を必ず持つ。

    本物の PR 一覧を使う実行は .github/workflows/merged-reachability.yml が担います。
    ここで gh を呼ぶと、認証の無い環境で黙って skip する検査になります。
    """
    for r in json.loads(POLICY.read_text(encoding="utf-8")).get("resolved", []):
        assert isinstance(r["pr"], int)
        assert r["reason"].strip()
        assert r["resolvedBy"].strip()


def test_締め切りより後のマージは保留する(tmp_path: Path, unreached_sha: str) -> None:
    """PR の一覧は実行時に取るが、git の履歴は基準ブランチの先端で止まっている。
    その間に入ったマージを「未到達」と誤って報告した(#118)。"""
    pr = _pr(9100, unreached_sha)
    pr["mergedAt"] = "2099-01-01T00:00:00Z"
    r = _run(tmp_path, [pr], "--cutoff", "2026-08-14T00:00:00Z")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "判定を保留した PR: 1 件" in r.stdout
    assert "到達していない PR: 0 件" in r.stdout


def test_締め切りより前のマージは判定する(tmp_path: Path, unreached_sha: str) -> None:
    """保留の仕組みが、本来落とすべきものまで通さないこと。"""
    pr = _pr(9101, unreached_sha)
    pr["mergedAt"] = "2026-08-13T00:00:00Z"
    r = _run(tmp_path, [pr], "--cutoff", "2026-08-14T00:00:00Z")
    assert r.returncode == 1
    assert "到達していない PR: 1 件" in r.stdout


def test_保留が0件でも件数を出力する(tmp_path: Path, reached_sha: str) -> None:
    r = _run(tmp_path, [_pr(1, reached_sha)], "--cutoff", "2099-01-01T00:00:00Z")
    assert "判定を保留した PR: 0 件" in r.stdout


def test_締め切りの時刻を出力する(tmp_path: Path) -> None:
    """いつ時点の履歴で判定したかが残らないと、保留の妥当性を後から確かめられない。"""
    r = _run(tmp_path, [], "--cutoff", "2026-08-14T00:00:00Z")
    assert "判定の締め切り: 2026-08-14T00:00:00" in r.stdout

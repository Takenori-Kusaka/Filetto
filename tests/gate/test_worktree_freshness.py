"""作業ツリーの鮮度の可視化(.claude/hooks/worktree-freshness.mjs)を検証する。

**止める装置ではありません。** 見えるようにする装置なので、確かめるのは
「見えるべきものが出力に現れるか」と「常に exit 0 で通ること」です。

実際のリポジトリを書き換えずに確かめるため、一時ディレクトリへ小さな git
リポジトリを作り、フックとその設定だけを写します。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/worktree-freshness.mjs"
CONFIG = ROOT / ".claude/worktree-freshness.json"
SETTINGS = ROOT / ".claude/settings.json"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。フックを実行できない場合は、見えるようになりません")
    return node


def _git(work: Path, *argv: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }
    import os

    return subprocess.run(  # noqa: S603
        ["git", *argv],
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env={**os.environ, **env},
    ).stdout.strip()


def _run(work: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [_node(), ".claude/hooks/worktree-freshness.mjs"],
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """origin と作業ツリーを持つ小さなリポジトリを作る。"""
    upstream = tmp_path / "upstream.git"
    work = tmp_path / "work"

    _init(upstream, bare=True)
    _init(work)

    (work / ".claude/hooks").mkdir(parents=True)
    shutil.copy(HOOK, work / ".claude/hooks/worktree-freshness.mjs")
    shutil.copy(CONFIG, work / ".claude/worktree-freshness.json")
    (work / ".claude/settings.json").write_text('{"permissions":{}}\n', encoding="utf-8")
    (work / "CLAUDE.md").write_text("初版\n", encoding="utf-8")

    _git(work, "add", "-A")
    _git(work, "commit", "-m", "初版")
    _git(work, "branch", "-M", "main")
    _git(work, "remote", "add", "origin", str(upstream))
    _git(work, "push", "-u", "origin", "main")
    return work


def _init(p: Path, *, bare: bool = False) -> None:
    p.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603
        ["git", "init", "-q", *(["--bare"] if bare else []), "-b", "main", str(p)],
        capture_output=True,
        check=True,
    )


def _advance_main(work: Path, path: str, body: str) -> None:
    """origin/main だけを進める。手元のブランチは取り残される。"""
    _git(work, "switch", "-q", "main")
    target = work / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "main を進める")
    _git(work, "push", "-q", "origin", "main")


def test_mainの最新なら差が無いことを出力する(repo: Path) -> None:
    r = _run(repo)
    assert r.returncode == 0
    assert "差はありません" in r.stdout


def test_ブランチにいることを出力する(repo: Path) -> None:
    _git(repo, "switch", "-q", "-c", "feature/x")
    r = _run(repo)
    assert r.returncode == 0
    assert "feature/x" in r.stdout
    assert "main ではありません" in r.stdout


def test_挙動を決めるファイルの差を列挙する(repo: Path) -> None:
    """実際に起きた事象。main が進み、ブランチに留まった側が古い設定で動く。"""
    _git(repo, "switch", "-q", "-c", "feature/stale")
    settings = '{"permissions":{"deny":["Bash(gh pr merge:*)"]}}\n'
    _advance_main(repo, ".claude/settings.json", settings)
    _advance_main(repo, "CLAUDE.md", "改訂された規約\n")
    _git(repo, "switch", "-q", "feature/stale")

    r = _run(repo)
    assert r.returncode == 0
    assert ".claude/settings.json" in r.stdout
    assert "CLAUDE.md" in r.stdout
    assert "コミット遅れています" in r.stdout
    assert "再起動" in r.stdout


def test_監視対象でないファイルの差は列挙しない(repo: Path) -> None:
    _git(repo, "switch", "-q", "-c", "feature/other")
    _advance_main(repo, "README.md", "関係のない変更\n")
    _git(repo, "switch", "-q", "feature/other")

    r = _run(repo)
    assert r.returncode == 0
    assert "差はありません" in r.stdout


def test_mainが遅れていればpullを促す(repo: Path) -> None:
    _advance_main(repo, "CLAUDE.md", "改訂\n")
    _git(repo, "reset", "-q", "--hard", "HEAD~1")
    r = _run(repo)
    assert r.returncode == 0
    assert "git pull" in r.stdout


def test_gitの外でも落ちない(tmp_path: Path) -> None:
    """フックが例外で落ちると、セッション開始が壊れます。"""
    work = tmp_path / "plain"
    (work / ".claude/hooks").mkdir(parents=True)
    shutil.copy(HOOK, work / ".claude/hooks/worktree-freshness.mjs")
    r = _run(work)
    assert r.returncode == 0


def test_設定が既定ブランチと監視対象を持つ() -> None:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert c["defaultBase"]
    assert ".claude/settings.json" in c["watchedPaths"]
    assert "CLAUDE.md" in c["watchedPaths"]


def test_SessionStartフックとして登録されている() -> None:
    """置いただけで走らないフックは、装置ではありません。"""
    s = json.loads(SETTINGS.read_text(encoding="utf-8"))
    cmds = [
        h["command"]
        for group in s["hooks"]["SessionStart"]
        for h in group["hooks"]
    ]
    assert any("worktree-freshness.mjs" in c for c in cmds)

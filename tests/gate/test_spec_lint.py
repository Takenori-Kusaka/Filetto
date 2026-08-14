"""受入基準の曖昧語検査(scripts/gate/spec-lint.mjs)を検証する。

検査そのものを検査します。**通ってはならないものが通らないこと**を否定側で確かめます。

除外の区間は、判定者が記入した文を機械で判定しないために置いています
(標準 5.7.4)。**除外が緩すぎれば受入基準の検査が骨抜きになり、厳しすぎれば
判定記録が `main` へ入りません。** どちらも確かめます。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/spec-lint.mjs"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


def _run(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [_node(), SCRIPT, str(target)],
        cwd=ROOT,
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


def _write(d: Path, name: str, body: str) -> None:
    (d / name).write_text(body, encoding="utf-8")


def test_曖昧語がなければ通る(docs: Path) -> None:
    _write(docs, "a.md", "システムは 3 秒以内に応答すること\n")
    r = _run(docs)
    assert r.returncode == 0, r.stdout + r.stderr


def test_否定_曖昧語があれば落ちる(docs: Path) -> None:
    _write(docs, "a.md", "システムは適切に応答すること\n")
    r = _run(docs)
    assert r.returncode == 1
    assert "適切に" in r.stdout + r.stderr


def test_除外区間の中は検査しない(docs: Path) -> None:
    """判定者の記入欄。標準 5.7.4 により機械で判定しない。"""
    _write(
        docs,
        "gate.md",
        "# 判定記録\n"
        "<!-- spec-lint-ignore start: 判定者の記入欄。標準 5.7.4 -->\n"
        "理由: テスト設計をいつ進めておくとよいかなどロードマップを決裁しにきてください\n"
        "<!-- spec-lint-ignore end -->\n",
    )
    r = _run(docs)
    assert r.returncode == 0, r.stdout + r.stderr


def test_除外した区間を件数と理由とともに出力する(docs: Path) -> None:
    reason = "判定者の記入欄。標準 5.7.4"
    _write(
        docs,
        "gate.md",
        f"<!-- spec-lint-ignore start: {reason} -->\n"
        "理由: なるべく事前にできるかが勝負\n"
        "<!-- spec-lint-ignore end -->\n",
    )
    r = _run(docs)
    assert r.returncode == 0
    assert "検査から外した区間: 1 件" in r.stdout
    assert reason in r.stdout


def test_除外が0件でも件数を出力する(docs: Path) -> None:
    _write(docs, "a.md", "システムは 3 秒以内に応答すること\n")
    r = _run(docs)
    assert "検査から外した区間: 0 件" in r.stdout


def test_除外区間の外は検査する(docs: Path) -> None:
    """判定記録の中でも、受入基準を転記した部分は検査されるべき。"""
    _write(
        docs,
        "gate.md",
        "<!-- spec-lint-ignore start: 判定者の記入欄 -->\n"
        "理由: なるべく早く\n"
        "<!-- spec-lint-ignore end -->\n"
        "受入基準: システムは適切に応答すること\n",
    )
    r = _run(docs)
    assert r.returncode == 1
    assert "適切に" in r.stdout + r.stderr


def test_否定_理由の無い除外は落ちる(docs: Path) -> None:
    """理由を書かずに検査を外す経路を作らない。"""
    _write(
        docs,
        "gate.md",
        "<!-- spec-lint-ignore start -->\n理由: なるべく早く\n<!-- spec-lint-ignore end -->\n",
    )
    r = _run(docs)
    assert r.returncode == 1
    assert "理由がありません" in r.stdout + r.stderr


def test_否定_閉じられていない除外は落ちる(docs: Path) -> None:
    """閉じ忘れると、以降のファイル全体が検査されなくなる。"""
    _write(docs, "gate.md", "<!-- spec-lint-ignore start: 判定者の記入欄 -->\n理由: なるべく早く\n")
    r = _run(docs)
    assert r.returncode == 1
    assert "閉じられていません" in r.stdout + r.stderr


def test_否定_対応する開始の無い終了は落ちる(docs: Path) -> None:
    _write(docs, "gate.md", "本文\n<!-- spec-lint-ignore end -->\n")
    r = _run(docs)
    assert r.returncode == 1
    assert "対応する spec-lint-ignore start がありません" in r.stdout + r.stderr


def test_否定_入れ子の除外は落ちる(docs: Path) -> None:
    _write(
        docs,
        "gate.md",
        "<!-- spec-lint-ignore start: 外 -->\n"
        "<!-- spec-lint-ignore start: 内 -->\n"
        "理由: なるべく\n"
        "<!-- spec-lint-ignore end -->\n",
    )
    r = _run(docs)
    assert r.returncode == 1
    assert "入れ子" in r.stdout + r.stderr


def test_行単位の逃がしは従来どおり効く(docs: Path) -> None:
    _write(docs, "a.md", "システムは適切に応答すること <!-- spec-lint-ok -->\n")
    r = _run(docs)
    assert r.returncode == 0, r.stdout + r.stderr


def test_コード塀の中は検査しない(docs: Path) -> None:
    _write(docs, "a.md", "```\n適切に\n```\n")
    r = _run(docs)
    assert r.returncode == 0, r.stdout + r.stderr


def test_コード塀の中の注記は区間として数えない(docs: Path) -> None:
    """説明のために書いた例が、本物の除外として働かないこと。"""
    body = (
        "説明:\n\n```markdown\n"
        "<!-- spec-lint-ignore start: 例 -->\n"
        "本文\n"
        "<!-- spec-lint-ignore end -->\n"
        "```\n"
    )
    _write(docs, "a.md", body)
    r = _run(docs)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "検査から外した区間: 0 件" in r.stdout


def test_検査した範囲を出力する(docs: Path) -> None:
    """何を検査したかが残らないと、通ったことの意味が分からない。"""
    _write(docs, "a.md", "本文\n")
    r = _run(docs)
    assert "検査した範囲:" in r.stdout


def test_本物の判定記録が通る() -> None:
    """リポジトリ全体で通ること。"""
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


def test_引用ブロックは検査しない(docs: Path) -> None:
    """閣議決定文書の条文や調査票の選択肢は、こちらの都合で書き換えられない(#104)。"""
    _write(docs, "spike.md", "> 社内情報の漏洩などのセキュリティリスクがある\n")
    r = _run(docs)
    assert r.returncode == 0, r.stdout + r.stderr


def test_引用として外した行を必ず出力する(docs: Path) -> None:
    _write(docs, "spike.md", "> AI を適切に使うスキル・知識があると感じる\n")
    r = _run(docs)
    assert "引用ブロックとして検査から外した行: 1 行" in r.stdout
    assert "spike.md" in r.stdout


def test_引用が0行でも件数を出力する(docs: Path) -> None:
    _write(docs, "a.md", "システムは 3 秒以内に応答すること\n")
    r = _run(docs)
    assert "引用ブロックとして検査から外した行: 0 行" in r.stdout


def test_否定_引用の外は検査する(docs: Path) -> None:
    _write(docs, "spike.md", "> 引用: など\n\n本文は適切に処理する\n")
    r = _run(docs)
    assert r.returncode == 1
    assert "適切に" in r.stdout + r.stderr


def test_否定_specs配下では引用も検査する(tmp_path: Path) -> None:
    """受入基準の正本。引用の形にすれば禁止語を書ける抜け道を作らない。"""
    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", work / "scripts")
    spec = work / "specs" / "F-999"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text("> システムは適切に応答すること\n", encoding="utf-8")
    (work / "docs").mkdir()
    (work / "docs" / "spike.md").write_text("> 調査票の選択肢は適切に選ぶ\n", encoding="utf-8")

    r = subprocess.run(  # noqa: S603
        [_node(), SCRIPT],
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    out = r.stdout + r.stderr
    # specs 配下の引用は落ちる
    assert "specs/F-999/spec.md:1" in out
    # docs 配下の引用は落ちず、外した行として数え上げられる
    assert "docs/spike.md:1" not in out
    assert "引用ブロックとして検査から外した行: 1 行" in out


def test_方針が禁止語と引用の扱いを持つ() -> None:
    import json

    policy = json.loads((ROOT / "scripts/gate/spec-lint-policy.json").read_text(encoding="utf-8"))
    assert policy["bannedWords"]
    assert policy["quoteBlock"]["exempt"] is True


def test_否定_禁止語が0語なら落ちる(tmp_path: Path) -> None:
    """0語のまま通すと、検査を実施していない状態を通過した記録として残る。"""
    import json

    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", work / "scripts")
    pol = work / "scripts/gate/spec-lint-policy.json"
    policy = json.loads(pol.read_text(encoding="utf-8"))
    policy["bannedWords"] = []
    pol.write_text(json.dumps(policy, ensure_ascii=False), encoding="utf-8")
    (work / "docs").mkdir()
    (work / "docs/a.md").write_text("本文\n", encoding="utf-8")
    r = subprocess.run(  # noqa: S603
        [_node(), SCRIPT],
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert r.returncode == 1
    assert "bannedWords" in r.stdout + r.stderr

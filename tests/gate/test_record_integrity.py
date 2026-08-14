"""記録の整合検査(scripts/gate/record-integrity.mjs)を検証する。

**AI が記録を落としても検出されること**が目的です(#145)。落とした記録を
見逃さないことを、否定側で確かめます。

Issue の一覧は `--issues-json` で与えます。gh とネットワークに依存する経路を
pytest へ持ち込むと、認証の無い環境で黙って skip する検査になります。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/gate/record-integrity.mjs"
CONFIG = ROOT / "scripts/gate/record-integrity.json"

RECORD = """# ゲート判定記録

| 項目 | 値 |
| --- | --- |
| ゲート | **G-4 機能仕様承認** |
| 対象 | F-001 |
| 判定者 | 価値責任者 |
| 判定日時 | 2026/08/13 |
| 結果 | 通過 |
"""

LEDGER = """# 技術負債台帳

| ID | 区分 | 内容 | 理由 | 兆候 | 期限 | 担当 | 状態 | 起票 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **D-001** | 未解決 | x | y | z | 2026-12-31 | 担当 | 未返却 | [#900](https://x/issues/900) |
"""


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。検査を実行できない場合は、実施していない状態になります")
    return node


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    work = tmp_path / "repo"
    shutil.copytree(ROOT / "scripts", work / "scripts")
    (work / "docs/gates").mkdir(parents=True)
    (work / "docs/gates/g4-F-001-2026-08-13.md").write_text(RECORD, encoding="utf-8")
    (work / "docs/debt-ledger.md").write_text(LEDGER, encoding="utf-8")
    (work / "specs/F-001").mkdir(parents=True)
    (work / "specs/F-001/spec.md").write_text("# F-001\n", encoding="utf-8")
    return work


def _issues(work: Path, rows: list[dict]) -> str:
    f = work / "issues.json"
    f.write_text(json.dumps(rows), encoding="utf-8")
    return str(f)


def _run(work: Path, issues: list[dict] | None = None, *argv: str):
    cmd = [_node(), SCRIPT, "--today", "2026-08-14"]
    if issues is not None:
        cmd += ["--issues-json", _issues(work, issues)]
    return subprocess.run(  # noqa: S603
        [*cmd, *argv],
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_整合していれば通る(repo: Path) -> None:
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 0, r.stdout + r.stderr


def test_すべての検査が件数を出力する(repo: Path) -> None:
    """0件のときも0件であることを出力する。"""
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    for n in ("検査1", "検査2", "検査3", "検査4", "検査5"):
        assert f"{n}" in r.stdout


def test_否定_判定日時が空欄なら落ちる(repo: Path) -> None:
    """本件の事例1。決裁は下りていたが記録が空欄のまま main にあった。"""
    p = repo / "docs/gates/g4-F-001-2026-08-13.md"
    body = p.read_text(encoding="utf-8").replace("| 判定日時 | 2026/08/13 |", "| 判定日時 |  |")
    p.write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "判定日時" in r.stdout + r.stderr


def test_否定_結果が空欄なら落ちる(repo: Path) -> None:
    p = repo / "docs/gates/g4-F-001-2026-08-13.md"
    body = p.read_text(encoding="utf-8").replace("| 結果 | 通過 |", "| 結果 | — |")
    p.write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1


def test_否定_標準に無い判定値は落ちる(repo: Path) -> None:
    """本件の事例4。「条件付き通過」は標準に無い。"""
    p = repo / "docs/gates/g4-F-001-2026-08-13.md"
    body = p.read_text(encoding="utf-8").replace("| 結果 | 通過 |", "| 結果 | 条件付き通過 |")
    p.write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "条件付き通過" in r.stdout + r.stderr


def test_否定_承認欄が通過なのに判定記録が無ければ落ちる(repo: Path) -> None:
    """本件の事例3。承認欄が G-2 と G-4 を混ぜていた。"""
    body = (
        "# F-001\n\n## 承認(G-2 / G-4)\n\n"
        "| ゲート | 判定者 | 判定日 | 結果 | 判定記録 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| G-4 | 日下 | 2026/08/14 | **通過** | [x](../../docs/gates/g4-F-999.md) |\n"
    )
    (repo / "specs/F-001/spec.md").write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "g4-F-999.md" in r.stdout + r.stderr


def test_否定_承認欄が通過なのに参照が無ければ落ちる(repo: Path) -> None:
    body = (
        "# F-001\n\n## 承認(G-2 / G-4)\n\n"
        "| ゲート | 判定者 | 判定日 | 結果 | 判定記録 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| G-4 | 日下 | 2026/08/14 | **通過** | — |\n"
    )
    (repo / "specs/F-001/spec.md").write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1


def test_否定_未返却なのにIssueが閉じていれば落ちる(repo: Path) -> None:
    """台帳が古いか、Issue を早く閉じたかのどちらか。"""
    r = _run(repo, [{"number": 900, "state": "CLOSED"}])
    assert r.returncode == 1
    assert "#900" in r.stdout + r.stderr


def test_否定_記録済みなのにIssueが開いていれば落ちる(repo: Path) -> None:
    """本件の事例2。閉じ忘れ。"""
    p = repo / "docs/debt-ledger.md"
    body = p.read_text(encoding="utf-8").replace("| 未返却 |", "| 記録済み |")
    p.write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "閉じ忘れ" in r.stdout + r.stderr


def test_否定_期限を過ぎて未返却なら落ちる(repo: Path) -> None:
    p = repo / "docs/debt-ledger.md"
    body = p.read_text(encoding="utf-8").replace("2026-12-31", "2026-08-01")
    p.write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "期限" in r.stdout + r.stderr


def test_期限が日付でない行を数え上げる(repo: Path) -> None:
    """黙って飛ばしません。読めなかったことを出力します。"""
    p = repo / "docs/debt-ledger.md"
    body = p.read_text(encoding="utf-8").replace("2026-12-31", "plan.md の作成前")
    p.write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "期限が日付として読めない行: 1 件" in r.stdout


def test_提示資料を判定記録として扱わない(repo: Path) -> None:
    """3列以上の表の見出し行を、項目と値として拾わないこと。"""
    body = (
        "# 提示\n\n"
        "| ゲート | 問い | 誰が決めるか | 状態 |\n"
        "| --- | --- | --- | --- |\n"
        "| G-4 | x | 人 | 未 |\n"
    )
    (repo / "docs/gates/g4-F-001-projection.md").write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "判定記録として扱わない" in r.stdout


def test_Issueを取得できないときは実施できないと出す(repo: Path) -> None:
    """取得できないことを理由に、検査を実施したことにしない。"""
    r = _run(repo, None)
    assert "実施できません" in r.stdout


def test_設定が理由と原則を書いている() -> None:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert c["why"].strip()
    assert "5.7.4" in c["principle"]
    assert c["resultVocabulary"]


PENDING_RECORD = """# ゲート判定記録

| 項目 | 値 |
| --- | --- |
| ゲート | **G-2 要件合意(再判定)** |
| 対象 | F-002 |
| 判定者 | 価値責任者 |
| 判定日時 | 判定待ち(2026-08-14 提示) |
| 結果 | 判定待ち(2026-08-14 提示) |
"""


def _write_pending(work: Path, date: str = "2026-08-14") -> None:
    body = PENDING_RECORD.replace("2026-08-14", date)
    (work / "docs/gates/g2-F-002-pending.md").write_text(body, encoding="utf-8")


def test_判定待ちは落とさない(repo: Path) -> None:
    """判定前の記録を PR で用意する運用がある。空欄と区別して明示させる。"""
    _write_pending(repo)
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 0, r.stdout + r.stderr


def test_判定待ちの件数を必ず出力する(repo: Path) -> None:
    _write_pending(repo)
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert "判定待ちの記録: 1 件" in r.stdout
    assert "2026-08-14 提示" in r.stdout


def test_判定待ちが0件でも件数を出力する(repo: Path) -> None:
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert "判定待ちの記録: 0 件" in r.stdout


def test_否定_判定待ちを放置すれば落ちる(repo: Path) -> None:
    """事例1(空欄のまま main に1日残った)は、放置を検出することで防ぐ。"""
    _write_pending(repo, "2026-08-01")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "判定期限" in r.stdout + r.stderr


def test_否定_提示日の無い判定待ちは空欄として落ちる(repo: Path) -> None:
    """いつから待っているかが分からなければ、放置を検出できない。"""
    body = PENDING_RECORD.replace("判定待ち(2026-08-14 提示)", "判定待ち")
    (repo / "docs/gates/g2-F-002-pending.md").write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "空欄" in r.stdout + r.stderr


def test_判定待ちは語彙検査の対象外(repo: Path) -> None:
    _write_pending(repo)
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert "検査4 判定値の語彙: 0 件" in r.stdout


def test_否定_判定待ちの記録を承認欄で通過と書けば落ちる(repo: Path) -> None:
    """判定していない記録を根拠に「通過」と書かせない。"""
    _write_pending(repo)
    body = (
        "# F-001\n\n## 承認(G-2 / G-4)\n\n"
        "| ゲート | 判定者 | 判定日 | 結果 | 判定記録 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| G-2 | 日下 | 2026/08/14 | **通過** | "
        "[x](../../docs/gates/g2-F-002-pending.md) |\n"
    )
    (repo / "specs/F-001/spec.md").write_text(body, encoding="utf-8")
    r = _run(repo, [{"number": 900, "state": "OPEN"}])
    assert r.returncode == 1
    assert "判定待ち" in r.stdout + r.stderr

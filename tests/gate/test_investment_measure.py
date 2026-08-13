"""投入量の測定(scripts/gate/investment-measure.mjs)を検証する。

分類は `scripts/gate/investment-classes.json` にあります。**規則そのものは運用で
変わるため、テストは「規則が守られること」と「未分類を通さないこと」を確かめます。**

PR の一覧は gh に依存するため、分類の関数を直接呼びます。ネットワークに依存する
経路を pytest へ持ち込むと、認証の無い環境で黙って skip する検査になります。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "scripts/gate/investment-classes.json"
SCRIPT = ROOT / "scripts/gate/investment-measure.mjs"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node が見つかりません。測定を実行できない場合は、記録が残りません")
    return node


def _eval(body: str) -> str:
    """スクリプトを import して式を評価する。"""
    src = textwrap.dedent(
        f"""
        import {{ classifyFile, classifyPr, globToRegExp }}
          from './scripts/gate/investment-measure.mjs';
        {body}
        """
    )
    f = ROOT / ".investment-probe.mjs"
    f.write_text(src, encoding="utf-8")
    try:
        r = subprocess.run(  # noqa: S603
            [_node(), str(f)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        return r.stdout.strip()
    finally:
        f.unlink(missing_ok=True)


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_分類規則が4区分をすべて持つ() -> None:
    ids = {c["id"] for c in _config()["classes"]}
    assert ids == {"process", "gate-record", "code", "product"}


def test_各区分が理由を持つ() -> None:
    for c in _config()["classes"]:
        assert c["label"].strip()
        assert c["note"].strip()
        assert c["patterns"]


def test_代表的なファイルが意図した区分になる() -> None:
    cases = {
        ".claude/settings.json": "process",
        "scripts/gate/spec-lint.mjs": "process",
        ".github/workflows/gate-g5.yml": "process",
        "tests/gate/test_spec_lint.py": "process",
        "docs/platform/README.md": "process",
        "docs/gates/g4-F-001-2026-08-13.md": "gate-record",
        "src/filetto/__init__.py": "code",
        "tests/test_package.py": "code",
        "specs/F-001/spec.md": "product",
        "docs/spikes/S0-001-graphify.md": "product",
        "context/decisions/0005-indexer-selection.md": "product",
    }
    out = _eval(
        "const cases = "
        + json.dumps(cases, ensure_ascii=False)
        + ";\n"
        + "for (const [f, want] of Object.entries(cases)) {\n"
        + "  const got = classifyFile(f);\n"
        + "  if (got !== want) console.log(`NG ${f}: ${got} !== ${want}`);\n"
        + "}\nconsole.log('done');"
    )
    assert "NG" not in out, out


def test_プロセス系のADRはプロセスへ入る() -> None:
    """context/decisions を丸ごと寄せると、プロダクトの技術判断と混ざる。"""
    out = _eval(
        "console.log(classifyFile('context/decisions/0013-license-check-spdx-expression.md'));"
        "console.log(classifyFile('context/decisions/0010-database-layer.md'));"
    )
    assert out.splitlines() == ["process", "product"]


def test_tests_gate_は実装コードではなくプロセスへ入る() -> None:
    """検査の装置のテストは、プロダクトの実装量ではない。"""
    out = _eval("console.log(classifyFile('tests/gate/test_spec_lint.py'));")
    assert out == "process"


def test_否定_規則に無いファイルは未分類になる() -> None:
    out = _eval("console.log(String(classifyFile('まだ無い領域/なにか.txt')));")
    assert out == "null"


def test_PRの区分は変更行数が最も多いものになる() -> None:
    files = [
        {"path": "src/filetto/a.py", "additions": 400, "deletions": 0},
        {"path": "docs/platform/README.md", "additions": 10, "deletions": 0},
    ]
    out = _eval(f"console.log(classifyPr({json.dumps(files)}).dominant);")
    assert out == "code"


def test_PRの未分類は握りつぶさない() -> None:
    files = [{"path": "まだ無い領域/x.txt", "additions": 1, "deletions": 0}]
    out = _eval(f"console.log(JSON.stringify(classifyPr({json.dumps(files)}).unclassified));")
    assert "まだ無い領域/x.txt" in out


def test_AI使用量の対象は作業ツリーの名前で絞る() -> None:
    """全プロジェクトを合算すると、本案件の投入量にならない。"""
    assert _config()["aiUsage"]["worktreePattern"]


def test_行数の対象が定義されている() -> None:
    ids = {t["id"] for t in _config()["lineCountTargets"]}
    assert {"code", "test", "doc"} <= ids


def test_台帳が存在する() -> None:
    """測っても置き場が無ければ、推移が残らない。"""
    ledger = ROOT / "docs/platform/investment-ledger.md"
    assert ledger.is_file()
    body = ledger.read_text(encoding="utf-8")
    assert "稼働時間" in body
    assert "AI 実行費" in body

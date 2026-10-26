"""F-001 受入基準13・14 と監査ログ(非機能の要求)の検査(WebUI と MCP の入口から)。

受入基準13: 利用者または AI エージェントがファイルのリネームを実行した場合、
システムは変更前の名前を操作履歴へ記録しなければならない。
受入基準14: 利用者または AI エージェントがファイルの移動を実行した場合、
システムは変更前のパスを操作履歴へ記録しなければならない。
監査ログ: 削除・リネーム・移動について、実行時刻・操作種別・対象パス・呼び出し経路を記録する。
リネーム・移動はメタデータの更新だけで行い、原本は書き換えない(受入基準1)。

受入基準と計画だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filetto.api import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "docs").mkdir(parents=True)
    (root / "archive").mkdir()
    (root / "docs" / "a.txt").write_text("あいう", encoding="utf-8")
    (root / "docs" / "c.txt").write_text("c", encoding="utf-8")
    return root


@pytest.fixture
def app(tmp_path: Path, original: Path):
    return create_app(original_root=original, db_path=tmp_path / "meta" / "f.db")


def _last(client: TestClient) -> dict:
    return client.get("/api/history").json()[-1]


def test_webui_rename_records_the_previous_name(app, original: Path) -> None:
    before = _snapshot(original)
    with TestClient(app) as client:
        res = client.post("/api/files/docs/a.txt/rename", json={"name": "b.txt"})
        assert res.status_code == 200
        assert res.json()["path"] == "docs/b.txt"
        entry = _last(client)
    assert entry["op"] == "rename"
    assert entry["before"] == "docs/a.txt"
    assert entry["after"] == "docs/b.txt"
    assert entry["via"] == "webui"
    assert _snapshot(original) == before


def test_webui_move_records_the_previous_path(app, original: Path) -> None:
    before = _snapshot(original)
    with TestClient(app) as client:
        res = client.post("/api/files/docs/a.txt/move", json={"to": "archive"})
        assert res.status_code == 200
        assert res.json()["path"] == "archive/a.txt"
        entry = _last(client)
    assert entry["op"] == "move"
    assert entry["before"] == "docs/a.txt"
    assert entry["after"] == "archive/a.txt"
    assert entry["via"] == "webui"
    assert _snapshot(original) == before


async def test_mcp_rename_and_move_record_previous_paths(app, original: Path) -> None:
    before = _snapshot(original)
    with TestClient(app) as client:
        await app.state.mcp.call_tool("rename_file", {"path": "docs/a.txt", "name": "b.txt"})
        await app.state.mcp.call_tool("move_file", {"path": "docs/b.txt", "to": "archive"})
        history = client.get("/api/history").json()
    rename, move = history[-2], history[-1]
    assert (rename["op"], rename["before"], rename["via"]) == ("rename", "docs/a.txt", "mcp")
    assert (move["op"], move["before"], move["via"]) == ("move", "docs/b.txt", "mcp")
    assert move["after"] == "archive/b.txt"
    assert _snapshot(original) == before


def test_history_records_time_of_operation(app) -> None:
    with TestClient(app) as client:
        start = datetime.now(UTC)
        client.post("/api/files/docs/a.txt/rename", json={"name": "b.txt"})
        at = datetime.fromisoformat(_last(client)["at"])
    assert at.tzinfo is not None
    assert start <= at <= datetime.now(UTC)


def test_renamed_file_is_found_under_its_new_path(app) -> None:
    with TestClient(app) as client:
        client.post("/api/files/docs/a.txt/rename", json={"name": "b.txt"})
        moved = client.post("/api/files/docs/b.txt/move", json={"to": "archive"})
        assert moved.status_code == 200
        assert moved.json()["path"] == "archive/b.txt"
        # 変更前の名前ではもう見つからない
        stale = client.post("/api/files/docs/a.txt/rename", json={"name": "x.txt"})
        assert stale.status_code == 404


def test_rename_onto_an_existing_file_is_refused_without_history(app) -> None:
    with TestClient(app) as client:
        count = len(client.get("/api/history").json())
        res = client.post("/api/files/docs/a.txt/rename", json={"name": "c.txt"})
        assert res.status_code == 409
        assert len(client.get("/api/history").json()) == count


def test_rename_of_a_missing_file_is_404(app) -> None:
    with TestClient(app) as client:
        res = client.post("/api/files/docs/none.txt/rename", json={"name": "b.txt"})
    assert res.status_code == 404


def test_rename_name_must_not_contain_a_separator(app) -> None:
    with TestClient(app) as client:
        res = client.post("/api/files/docs/a.txt/rename", json={"name": "archive/b.txt"})
    assert res.status_code == 400


async def test_delete_is_recorded_with_its_route(app) -> None:
    with TestClient(app) as client:
        client.delete("/api/files/docs/a.txt")
        await app.state.mcp.call_tool("delete_file", {"path": "docs/c.txt"})
        history = client.get("/api/history").json()
    webui, mcp = history[-2], history[-1]
    assert (webui["op"], webui["before"], webui["via"]) == ("delete", "docs/a.txt", "webui")
    assert (mcp["op"], mcp["before"], mcp["via"]) == ("delete", "docs/c.txt", "mcp")

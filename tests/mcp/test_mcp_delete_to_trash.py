"""F-001 受入基準3 の検査(MCP の入口から)。

受入基準3: AI エージェントが MCP からファイルの削除を実行した場合、
システムはファイルをゴミ箱へ移動し、原本の実体を削除してはならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import hashlib
from pathlib import Path

import pytest

from filetto.mcp import create_mcp
from filetto.storage import OriginalStore
from filetto.trash import TrashStore

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
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("あいう", encoding="utf-8")
    (root / "sub" / "b.txt").write_text("b", encoding="utf-8")
    return root


@pytest.fixture
def trash(tmp_path: Path, original: Path) -> TrashStore:
    return TrashStore(tmp_path / "meta" / "f.db", OriginalStore(original))


async def test_mcp_delete_moves_the_file_to_trash(trash: TrashStore) -> None:
    server = create_mcp(trash)

    result = await server.call_tool("delete_file", {"path": "sub/b.txt"})

    assert not result.is_error
    assert [e.path for e in trash.list()] == ["sub/b.txt"]


async def test_mcp_delete_does_not_remove_the_original_entity(
    trash: TrashStore, original: Path
) -> None:
    server = create_mcp(trash)
    before = _snapshot(original)

    await server.call_tool("delete_file", {"path": "a.txt"})
    await server.call_tool("delete_file", {"path": "sub/b.txt"})

    assert _snapshot(original) == before
    assert [e.path for e in trash.list()] == ["a.txt", "sub/b.txt"]


async def test_mcp_delete_of_a_missing_file_fails_without_trashing(trash: TrashStore) -> None:
    """失敗の伝え方(例外か is_error の結果か)は問わない。失敗として返り、ゴミ箱に入らない"""
    server = create_mcp(trash)
    try:
        result = await server.call_tool("delete_file", {"path": "missing.txt"})
        failed = result.is_error
    except Exception:  # noqa: BLE001
        failed = True
    assert failed
    assert trash.list() == []


async def test_mcp_and_webui_share_one_trash(tmp_path: Path, original: Path) -> None:
    """どちらの経路で削除しても、同じゴミ箱に入る(経路で可逆性の水準を変えない)"""
    from fastapi.testclient import TestClient

    from filetto.api import create_app

    app = create_app(original_root=original, db_path=tmp_path / "meta" / "f.db")
    with TestClient(app) as client:
        assert client.delete("/api/files/a.txt").status_code == 200
        await app.state.mcp.call_tool("delete_file", {"path": "sub/b.txt"})
        assert [e["path"] for e in client.get("/api/trash").json()] == ["a.txt", "sub/b.txt"]

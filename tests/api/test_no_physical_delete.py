"""F-001 受入基準4 の検査(公開されている経路の列挙に対する検査)。

受入基準4: システムは物理削除を行う API を WebUI と MCP のいずれにも公開してはならない。

「無いこと」の検査は実装が無くても通りやすい。そのため、公開されている経路を列挙し、
(1) 物理削除を名乗る経路が無いこと、(2) 公開されている全ての書き込みの経路を実際に呼んでも
原本の実体が1つも消えないこと、の両方を見る。受入基準だけを入力に書いた検査です。
"""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filetto.api import create_app

pytestmark = pytest.mark.anyio

FORBIDDEN = ("purge", "destroy", "permanent", "hard", "physical", "erase", "wipe", "unlink", "rm")


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
    root.mkdir()
    (root / "a.txt").write_text("あいう", encoding="utf-8")
    return root


@pytest.fixture
def app(tmp_path: Path, original: Path):
    return create_app(original_root=original, db_path=tmp_path / "meta" / "f.db")


def _rest_routes(app) -> list[tuple[str, str]]:
    return [
        (method, route.path)
        for route in app.routes
        for method in (getattr(route, "methods", None) or ())
        if method not in ("GET", "HEAD", "OPTIONS")
    ]


def _words(text: str) -> set[str]:
    return {w for w in text.lower().replace("-", "_").replace("/", "_").split("_") if w}


async def test_mcp_is_exposed(app) -> None:
    """MCP の経路が存在する(存在しないことで基準4 が成り立つ状態にしない)"""
    tools = await app.state.mcp.list_tools()
    assert tools


async def test_no_route_or_tool_is_named_as_physical_delete(app) -> None:
    rest = [path for _, path in _rest_routes(app)]
    tools = [t.name for t in await app.state.mcp.list_tools()]
    named = [n for n in rest + tools if _words(n) & set(FORBIDDEN)]
    assert named == []


async def test_every_exposed_write_keeps_the_original(app, original: Path) -> None:
    before = _snapshot(original)
    with TestClient(app) as client:
        for method, path in _rest_routes(app):
            target = path.replace("{path:path}", "a.txt").replace("{path}", "a.txt")
            client.request(method, target)
        for tool in await app.state.mcp.list_tools():
            props = tool.input_schema.get("properties", {})
            args = {name: "a.txt" for name in props}
            try:
                await app.state.mcp.call_tool(tool.name, args)
            except Exception:  # noqa: BLE001 呼び出しの成否ではなく、原本が残るかを見る
                pass
    assert _snapshot(original) == before

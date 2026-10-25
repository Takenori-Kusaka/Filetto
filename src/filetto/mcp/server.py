"""MCP のツール(F-001 受入基準3・4)。

削除は WebUI と同じゴミ箱へ入れる(経路で可逆性の水準を変えない)。物理削除のツールは置かない。
AI が呼ぶ経路には確認の UI が無いため、可逆性は実装で担保する。
"""

from __future__ import annotations

from mcp.server import MCPServer

from filetto.trash import TrashStore


def create_mcp(trash: TrashStore) -> MCPServer:
    server = MCPServer("Filetto")

    @server.tool()
    def delete_file(path: str) -> dict[str, str]:
        """ファイルをゴミ箱へ移す。原本の実体は削除しない。ゴミ箱からは復元できる"""
        entry = trash.trash(path)
        return {"path": entry.path, "trashed_at": entry.trashed_at.isoformat()}

    @server.tool()
    def list_trash() -> list[dict[str, str]]:
        """ゴミ箱の一覧(削除前のパスと、ゴミ箱へ入れた時刻)"""
        return [{"path": e.path, "trashed_at": e.trashed_at.isoformat()} for e in trash.list()]

    return server

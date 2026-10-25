"""F-001 受入基準2 の検査(WebUI の入口から)。

受入基準2: 利用者が WebUI からファイルの削除を実行した場合、
システムはファイルをゴミ箱へ移動し、原本の実体を削除してはならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filetto.api import create_app


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
def client(tmp_path: Path, original: Path) -> TestClient:
    return TestClient(create_app(original_root=original, db_path=tmp_path / "meta" / "f.db"))


def test_delete_moves_the_file_to_trash(client: TestClient) -> None:
    res = client.delete("/api/files/sub/b.txt")

    assert res.status_code == 200
    assert res.json()["path"] == "sub/b.txt"
    trash = client.get("/api/trash")
    assert trash.status_code == 200
    assert [e["path"] for e in trash.json()] == ["sub/b.txt"]


def test_delete_does_not_remove_the_original_entity(client: TestClient, original: Path) -> None:
    before = _snapshot(original)

    assert client.delete("/api/files/a.txt").status_code == 200
    assert client.delete("/api/files/sub/b.txt").status_code == 200

    assert _snapshot(original) == before


def test_delete_of_a_missing_file_is_404(client: TestClient) -> None:
    assert client.delete("/api/files/missing.txt").status_code == 404
    assert client.get("/api/trash").json() == []


def test_delete_of_a_trashed_file_is_409(client: TestClient) -> None:
    assert client.delete("/api/files/a.txt").status_code == 200
    assert client.delete("/api/files/a.txt").status_code == 409


def test_delete_outside_the_original_is_refused(client: TestClient, original: Path) -> None:
    (original.parent / "outside.txt").write_text("外", encoding="utf-8")
    res = client.delete("/api/files/..%2Foutside.txt")
    assert res.status_code in (400, 404)
    assert (original.parent / "outside.txt").exists()
    assert client.get("/api/trash").json() == []

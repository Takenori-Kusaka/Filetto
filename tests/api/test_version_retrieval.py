"""F-001 受入基準16 の検査(過去の版の取得、WebUI の入口から)。

受入基準16: 利用者が過去のバージョンを指定して取得を実行した場合、
システムは当該バージョンの内容を返さなければならない。
版の取得は読むだけで、原本は書き換えない(受入基準1)。

受入基準と計画だけを入力に書いた検査です(実装を読まずに書いています)。
"""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filetto.api import create_app
from filetto.version import LoreVersionStore


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
    (root / "docs" / "a.txt").write_text("v3", encoding="utf-8")
    (root / "docs" / "new.txt").write_text("x", encoding="utf-8")
    return root


@pytest.fixture
def versions(tmp_path: Path) -> LoreVersionStore:
    store = LoreVersionStore(tmp_path / "lore")
    store.save("docs/a.txt", b"v1")
    store.save("docs/a.txt", "v2 あいう".encode())
    return store


@pytest.fixture
def client(tmp_path: Path, original: Path, versions: LoreVersionStore) -> TestClient:
    app = create_app(original_root=original, db_path=tmp_path / "meta" / "f.db", versions=versions)
    return TestClient(app)


def test_versions_are_listed_oldest_first(client: TestClient) -> None:
    res = client.get("/api/files/docs/a.txt/versions")
    assert res.status_code == 200
    listed = res.json()
    assert len(listed) == 2
    assert all(v["path"] == "docs/a.txt" for v in listed)
    assert listed[0]["saved_at"] <= listed[1]["saved_at"]


def test_a_specified_past_version_returns_its_content(client: TestClient) -> None:
    first, second = client.get("/api/files/docs/a.txt/versions").json()
    res = client.get(f"/api/files/docs/a.txt/versions/{first['id']}")
    assert res.status_code == 200
    assert res.content == b"v1"
    res = client.get(f"/api/files/docs/a.txt/versions/{second['id']}")
    assert res.content == "v2 あいう".encode()


def test_unknown_version_is_404(client: TestClient) -> None:
    res = client.get("/api/files/docs/a.txt/versions/999999")
    assert res.status_code == 404


def test_file_without_versions_lists_none(client: TestClient) -> None:
    res = client.get("/api/files/docs/new.txt/versions")
    assert res.status_code == 200
    assert res.json() == []


def test_missing_file_is_404(client: TestClient) -> None:
    assert client.get("/api/files/docs/none.txt/versions").status_code == 404


def test_versions_follow_a_renamed_file(client: TestClient) -> None:
    """リネーム後も、いまの名前で過去の版を取れる(原本のパスで保管している版)"""
    client.post("/api/files/docs/a.txt/rename", json={"name": "b.txt"})
    listed = client.get("/api/files/docs/b.txt/versions").json()
    assert len(listed) == 2
    res = client.get(f"/api/files/docs/b.txt/versions/{listed[0]['id']}")
    assert res.content == b"v1"


def test_retrieval_does_not_write_the_original(client: TestClient, original: Path) -> None:
    before = _snapshot(original)
    first = client.get("/api/files/docs/a.txt/versions").json()[0]
    client.get(f"/api/files/docs/a.txt/versions/{first['id']}")
    assert _snapshot(original) == before

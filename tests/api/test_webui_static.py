"""WebUI の配信(ADR-0003、F-001 Task-12)。

画面は SvelteKit の静的出力を FastAPI から配信し、データは /api/** の JSON から取る。
画面の経路(例: /trash)を直接開いても画面が返り、API の経路は画面に置き換わらないことを見る。
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filetto.api import create_app

MARKER = "filetto-web-index"


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    root.mkdir()
    (root / "a.txt").write_text("あいう", encoding="utf-8")
    return root


@pytest.fixture
def web_dir(tmp_path: Path) -> Path:
    build = tmp_path / "build"
    (build / "_app").mkdir(parents=True)
    (build / "index.html").write_text(f"<html>{MARKER}</html>", encoding="utf-8")
    (build / "_app" / "start.js").write_text("export const ok = 1;", encoding="utf-8")
    return build


def _client(tmp_path: Path, original: Path, web_dir: Path | None) -> TestClient:
    return TestClient(
        create_app(original_root=original, db_path=tmp_path / "meta" / "f.db", web_dir=web_dir)
    )


def test_root_serves_the_webui(tmp_path: Path, original: Path, web_dir: Path) -> None:
    res = _client(tmp_path, original, web_dir).get("/")
    assert res.status_code == 200
    assert MARKER in res.text


def test_screen_path_opened_directly_serves_the_webui(
    tmp_path: Path, original: Path, web_dir: Path
) -> None:
    res = _client(tmp_path, original, web_dir).get("/trash")
    assert res.status_code == 200
    assert MARKER in res.text


def test_built_assets_are_served(tmp_path: Path, original: Path, web_dir: Path) -> None:
    res = _client(tmp_path, original, web_dir).get("/_app/start.js")
    assert res.status_code == 200
    assert "export const ok" in res.text


def test_api_is_not_replaced_by_the_webui(tmp_path: Path, original: Path, web_dir: Path) -> None:
    client = _client(tmp_path, original, web_dir)
    client.delete("/api/files/a.txt")
    listed = client.get("/api/trash")
    assert listed.json()[0]["path"] == "a.txt"
    missing = client.get("/api/no-such-route")
    assert missing.status_code == 404
    assert MARKER not in missing.text


def test_without_web_dir_only_the_api_is_served(tmp_path: Path, original: Path) -> None:
    client = _client(tmp_path, original, None)
    assert client.get("/api/trash").status_code == 200
    assert client.get("/").status_code == 404

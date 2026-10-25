"""F-001 受入基準5・6 の検査(WebUI の入口から)。

受入基準5: 利用者がゴミ箱内のファイルに対して復元を実行した場合、
システムは削除前のパスへファイルを戻さなければならない。
受入基準6: 復元先のパスに同名のファイルが存在する場合、
システムは HTTP 409 を返し、復元を実行してはならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
ゴミ箱は論理削除(原本の実体はその場に残る)のため、「同名のファイルが存在する」は、
ゴミ箱へ入れた後に、削除前のパスへ別のファイルが置かれた状態として作る。
"""

import hashlib
import os
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


def _trashed(client: TestClient) -> list[str]:
    return [item["path"] for item in client.get("/api/trash").json()]


def test_restore_returns_the_file_to_its_path_before_deletion(
    client: TestClient, original: Path
) -> None:
    before = _snapshot(original)
    assert client.delete("/api/files/sub/b.txt").status_code == 200

    res = client.post("/api/trash/sub/b.txt/restore")

    assert res.status_code == 200
    assert res.json()["path"] == "sub/b.txt"
    assert _trashed(client) == []
    assert _snapshot(original) == before


def test_restored_file_can_be_deleted_again(client: TestClient) -> None:
    client.delete("/api/files/a.txt")
    client.post("/api/trash/a.txt/restore")

    assert client.delete("/api/files/a.txt").status_code == 200
    assert _trashed(client) == ["a.txt"]


def test_restore_of_a_path_not_in_trash_is_404(client: TestClient) -> None:
    assert client.post("/api/trash/a.txt/restore").status_code == 404


def test_restore_outside_the_original_is_rejected(client: TestClient) -> None:
    assert client.post("/api/trash/..%2Foutside.txt/restore").status_code in (400, 404)


def test_restore_onto_a_same_named_file_is_409_and_not_restored(
    client: TestClient, original: Path
) -> None:
    client.delete("/api/files/a.txt")
    # ゴミ箱へ入れた後、削除前のパスへ別のファイルが置かれた
    target = original / "a.txt"
    target.unlink()
    target.write_text("別のファイル", encoding="utf-8")
    st = target.stat()
    os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    placed = _snapshot(original)

    res = client.post("/api/trash/a.txt/restore")

    assert res.status_code == 409
    assert _trashed(client) == ["a.txt"]
    assert _snapshot(original) == placed

"""F-001 受入基準11・12 の検査(ゴミ箱の一覧の API)。

受入基準11: 利用者がゴミ箱の一覧を開いた場合、システムは各項目に完全削除までの残日数を
表示しなければならない。
受入基準12: システムは完全削除の予告をトースト・ポップアップ・バッジ・メールのいずれによっても
通知してはならない。

受入基準だけを入力に書いた検査です(実装を読まずに書いています)。
画面は WebUI の技術を決めた後に作る。ここでは一覧の API が残日数を返すことと、
通知の仕組みを持たないことを見る。
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filetto.api import create_app
from filetto.config import RETENTION_ENV

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def original(tmp_path: Path) -> Path:
    root = tmp_path / "original"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("a", encoding="utf-8")
    return root


def _client(tmp_path: Path, original: Path) -> TestClient:
    return TestClient(create_app(original_root=original, db_path=tmp_path / "meta" / "f.db"))


def test_api_lists_remaining_days(
    tmp_path: Path, original: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(RETENTION_ENV, "7")
    client = _client(tmp_path, original)
    client.delete("/api/files/a.txt")

    assert client.get("/api/trash").json()[0]["remaining_days"] == 7


def test_api_lists_unlimited_as_null(
    tmp_path: Path, original: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(RETENTION_ENV, "unlimited")
    client = _client(tmp_path, original)
    client.delete("/api/files/a.txt")

    assert client.get("/api/trash").json()[0]["remaining_days"] is None


def test_no_mail_or_notification_is_sent_anywhere() -> None:
    """メール送信・通知の仕組みをソースと画面に持たない"""
    pattern = re.compile(r"smtplib|email\.mime|new Notification|showNotification", re.I)
    # 画面は手で書いたソース(web/src)だけを見る。node_modules・build は依存と生成物
    files = [*(ROOT / "src").rglob("*.py"), *(ROOT / "web" / "src").rglob("*")]
    hits = [str(p) for p in files if p.is_file() and pattern.search(p.read_text("utf-8"))]
    assert hits == []

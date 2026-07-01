"""多智能体协作模式元数据国际化 API 测试。"""

from fastapi.testclient import TestClient
import pytest

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage


MODE_IDS = {
    "sequential",
    "parallel",
    "hierarchical",
    "peer_to_peer",
    "hybrid",
}
ZH_NAMES = {"顺序协作", "并行协作", "层级协作", "对等协作", "混合模式"}
EN_NAMES = {
    "Sequential Collaboration",
    "Parallel Collaboration",
    "Hierarchical Collaboration",
    "Peer-to-Peer Collaboration",
    "Hybrid Collaboration",
}
RU_NAMES = {
    "Последовательное взаимодействие",
    "Параллельное взаимодействие",
    "Иерархическое взаимодействие",
    "Одноранговое взаимодействие",
    "Гибридное взаимодействие",
}


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    test_client = TestClient(web_app.app)
    response = test_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )
    assert response.status_code == 200
    return test_client


def _get_modes(client: TestClient, headers=None) -> dict:
    response = client.get("/api/multi-agent/modes", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    return payload["modes"]


def _mode_names(modes: dict) -> set[str]:
    return {mode["name"] for mode in modes.values()}


def test_modes_default_lang_zh(client):
    assert _mode_names(_get_modes(client)) == ZH_NAMES


def test_modes_xuserlang_en(client):
    assert _mode_names(_get_modes(client, {"X-User-Lang": "en"})) == EN_NAMES


def test_modes_xuserlang_ru(client):
    assert _mode_names(_get_modes(client, {"X-User-Lang": "ru"})) == RU_NAMES


def test_modes_unsupported_lang_falls_back_en(client):
    unsupported = _get_modes(client, {"X-User-Lang": "ja"})
    english = _get_modes(client, {"X-User-Lang": "en"})

    assert unsupported == english
    assert _mode_names(unsupported) == EN_NAMES


def test_modes_response_shape_unchanged(client):
    assert set(_get_modes(client)) == MODE_IDS


def test_modes_icons_not_translated(client):
    assert _get_modes(client, {"X-User-Lang": "ru"})["sequential"]["icon"] == "🔄"

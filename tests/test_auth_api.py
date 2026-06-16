"""认证 API 最小闭环测试。"""

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage


def _configure_auth_test_app(tmp_path, monkeypatch):
    """将认证 API 测试隔离到临时 SQLite 数据库。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    return TestClient(web_app.app), db_path


def _login(client: TestClient, username: str = "admin", password: str = "admin-secret"):
    """执行登录并返回响应 JSON。"""
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_initial_admin_can_login_and_me_returns_current_user(tmp_path, monkeypatch):
    """初始管理员应可登录，Cookie 写入后 /me 返回当前用户。"""
    client, db_path = _configure_auth_test_app(tmp_path, monkeypatch)

    data = _login(client)

    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"
    assert data["csrf_token"]
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]
    assert "lpos_session" in client.cookies

    me_response = client.get("/api/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["user"]["username"] == "admin"
    assert db_path.exists()


def test_logout_revokes_session_and_me_returns_401(tmp_path, monkeypatch):
    """注销后服务端应拒绝旧 session。"""
    client, _ = _configure_auth_test_app(tmp_path, monkeypatch)
    _login(client)

    logout_response = client.post("/api/auth/logout")
    me_response = client.get("/api/auth/me")

    assert logout_response.status_code == 200
    assert logout_response.json()["success"] is True
    assert me_response.status_code == 401


def test_change_password_invalidates_old_password_and_accepts_new_password(tmp_path, monkeypatch):
    """改密后旧密码不可用，新密码可登录。"""
    client, _ = _configure_auth_test_app(tmp_path, monkeypatch)
    _login(client)

    change_response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": "admin-secret",
            "new_password": "new-admin-secret",
        },
    )

    assert change_response.status_code == 200
    assert change_response.json()["success"] is True

    old_password_client = TestClient(web_app.app)
    old_login = old_password_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )
    assert old_login.status_code == 401

    new_password_client = TestClient(web_app.app)
    new_login = new_password_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "new-admin-secret"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["user"]["username"] == "admin"


def test_me_without_session_returns_401(tmp_path, monkeypatch):
    """未登录访问 /me 应返回 401。"""
    client, _ = _configure_auth_test_app(tmp_path, monkeypatch)

    response = client.get("/api/auth/me")

    assert response.status_code == 401

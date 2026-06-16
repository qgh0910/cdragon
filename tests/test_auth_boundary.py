"""默认认证边界与匿名白名单测试。"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage


def _configure_auth_boundary_test_app(tmp_path, monkeypatch):
    """将认证边界测试隔离到临时认证数据库。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    return TestClient(web_app.app)


def _login(client: TestClient):
    """登录测试管理员。"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )
    assert response.status_code == 200
    return response


def test_business_api_requires_login_by_default(tmp_path, monkeypatch):
    """除匿名白名单外，未登录访问业务 /api/* 应返回 401。"""
    client = _configure_auth_boundary_test_app(tmp_path, monkeypatch)

    response = client.get("/api/multi-agent/teams")

    assert response.status_code == 401


def test_anonymous_whitelist_remains_accessible(tmp_path, monkeypatch):
    """首页、健康检查和登录接口应保持匿名可访问。"""
    client = _configure_auth_boundary_test_app(tmp_path, monkeypatch)

    root_response = client.get("/")
    health_response = client.get("/api/health")
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )

    assert root_response.status_code == 200
    assert health_response.status_code == 200
    assert login_response.status_code == 200


def test_logged_in_user_can_access_business_api(tmp_path, monkeypatch):
    """登录后应能继续访问业务 API。"""
    client = _configure_auth_boundary_test_app(tmp_path, monkeypatch)
    _login(client)

    response = client.get("/api/multi-agent/teams")

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_cors_no_longer_uses_wildcard_origin_with_credentials():
    """启用 credentials 时，CORS 不能继续使用通配来源。"""
    cors_middleware = next(
        middleware
        for middleware in web_app.app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_credentials"] is True
    assert "*" not in cors_middleware.kwargs["allow_origins"]

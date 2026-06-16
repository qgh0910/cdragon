"""知识库 collections 基础 API 测试。"""

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.kb import registry


def _configure_kb_api_test_app(tmp_path, monkeypatch):
    """将知识库 API 测试隔离到临时认证数据库。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    return TestClient(web_app.app), db_path


def _login(client: TestClient, username: str = "admin", password: str = "admin-secret"):
    """登录指定用户。"""
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["user"]


def _create_regular_user(username: str, password: str = "user-secret") -> dict:
    """创建普通测试用户。"""
    return storage.create_user(
        username=username,
        display_name=username,
        password_hash=generate_password_hash(password),
        role="user",
    )


def test_user_can_create_list_view_and_delete_own_user_collection(tmp_path, monkeypatch):
    """普通用户应可管理自己的用户知识库。"""
    client, _ = _configure_kb_api_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    _login(client, "reviewer", "user-secret")

    create_response = client.post(
        "/api/kb/collections",
        json={
            "scope": "user",
            "display_name": "我的合同模板",
            "description": "个人常用合同模板",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()["collection"]
    assert created["scope"] == "user"
    assert created["owner_user_id"] == user["id"]
    assert created["display_name"] == "我的合同模板"

    list_response = client.get("/api/kb/collections")
    detail_response = client.get(f"/api/kb/collections/{created['id']}")
    delete_response = client.delete(f"/api/kb/collections/{created['id']}")
    after_delete_response = client.get(f"/api/kb/collections/{created['id']}")

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["collections"]] == [created["id"]]
    assert detail_response.status_code == 200
    assert detail_response.json()["collection"]["id"] == created["id"]
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
    assert after_delete_response.status_code == 404


def test_user_cannot_create_public_collection(tmp_path, monkeypatch):
    """普通用户不能创建公共知识库。"""
    client, _ = _configure_kb_api_test_app(tmp_path, monkeypatch)
    _create_regular_user("reviewer")
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/kb/collections",
        json={"scope": "public", "display_name": "法规案例库"},
    )

    assert response.status_code == 403


def test_admin_can_create_list_view_and_delete_public_collection(tmp_path, monkeypatch):
    """管理员应可管理公共知识库。"""
    client, _ = _configure_kb_api_test_app(tmp_path, monkeypatch)
    admin = _login(client)

    create_response = client.post(
        "/api/kb/collections",
        json={
            "scope": "public",
            "display_name": "法规案例库",
            "description": "公共法规、案例、企业制度",
        },
    )
    created = create_response.json()["collection"]

    list_response = client.get("/api/kb/collections?scope=public")
    detail_response = client.get(f"/api/kb/collections/{created['id']}")
    delete_response = client.delete(f"/api/kb/collections/{created['id']}")

    assert create_response.status_code == 200
    assert created["scope"] == "public"
    assert created["owner_user_id"] is None
    assert created["created_by"] == admin["id"]
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["collections"]] == [created["id"]]
    assert detail_response.status_code == 200
    assert detail_response.json()["collection"]["scope"] == "public"
    assert delete_response.status_code == 200


def test_collection_list_only_returns_current_user_visible_collections(tmp_path, monkeypatch):
    """列表接口只能返回当前用户可见知识库。"""
    client, _ = _configure_kb_api_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    other_user = _create_regular_user("other")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="公共法规库",
        created_by="usr_admin",
    )
    own_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="我的模板",
        created_by=user["id"],
    )
    registry.create_knowledge_base(
        scope="user",
        owner_user_id=other_user["id"],
        display_name="他人模板",
        created_by=other_user["id"],
    )
    registry.register_legacy_knowledge_base(
        display_name="旧库",
        collection_name="legacy_collection",
        created_by="usr_admin",
    )
    _login(client, "reviewer", "user-secret")

    all_response = client.get("/api/kb/collections")
    mine_response = client.get("/api/kb/collections?scope=mine")
    public_response = client.get("/api/kb/collections?scope=public")

    assert all_response.status_code == 200
    assert {item["id"] for item in all_response.json()["collections"]} == {public_kb["id"], own_kb["id"]}
    assert [item["id"] for item in mine_response.json()["collections"]] == [own_kb["id"]]
    assert [item["id"] for item in public_response.json()["collections"]] == [public_kb["id"]]


def test_collection_list_includes_document_count(tmp_path, monkeypatch):
    """列表接口应返回资料数，供前端下拉框显示。"""
    client, _ = _configure_kb_api_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    own_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="我的法律资料",
        created_by=user["id"],
        collection_name="user_contract_docs",
    )
    monkeypatch.setattr(
        web_app,
        "_get_collection_document_count",
        lambda collection_name: 135 if collection_name == "user_contract_docs" else 0,
    )
    _login(client, "reviewer", "user-secret")

    response = client.get("/api/kb/collections")

    assert response.status_code == 200
    assert response.json()["collections"] == [
        {
            **own_kb,
            "document_count": 135,
        }
    ]

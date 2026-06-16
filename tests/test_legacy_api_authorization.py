"""legacy 业务接口登录与权限隔离测试。"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.kb import registry


class _FakeMemory:
    """测试用记忆对象。"""

    def to_dict(self):
        return {"id": "mem_1", "content": "记忆内容"}


class _FakeMemoryAgent:
    """避免测试触发真实记忆模型和 LLM。"""

    def store_memory(self, **kwargs):
        return _FakeMemory()


def _configure_legacy_test_app(tmp_path, monkeypatch):
    """隔离认证库、上传根目录和运行态缓存。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True)

    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    monkeypatch.setattr(web_app.settings, "upload_root_path", str(upload_root))
    web_app.collection_name_mapping.clear()
    web_app.rag_agents.clear()
    web_app.session_histories.clear()
    web_app.memory_agents.clear()
    return TestClient(web_app.app), upload_root


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


def test_legacy_business_apis_require_login(tmp_path, monkeypatch):
    """未登录访问 legacy RAG、上传审计、history 和 memory 接口应返回 401。"""
    client, _ = _configure_legacy_test_app(tmp_path, monkeypatch)

    responses = [
        client.get("/api/rag/mappings"),
        client.get("/api/uploads/audit"),
        client.get("/api/rag/document/legacy_collection/doc_1"),
        client.delete("/api/rag/clear/legacy_collection"),
        client.get("/api/history/shared_session"),
        client.post(
            "/api/memory/store",
            json={
                "content": "记忆内容",
                "memory_type": "short_term",
                "importance": 3,
                "session_id": "shared_session",
            },
        ),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401, 401, 401, 401]


def test_regular_user_only_sees_visible_mappings_and_own_audit(tmp_path, monkeypatch):
    """普通用户不能通过 legacy mappings/audit 看到全局资料库和他人审计。"""
    client, upload_root = _configure_legacy_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    other_user = _create_regular_user("other")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="public_law",
        created_by="usr_admin",
    )
    own_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="own_templates",
        created_by=user["id"],
    )
    other_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=other_user["id"],
        display_name="other_templates",
        created_by=other_user["id"],
    )
    legacy_kb = registry.register_legacy_knowledge_base(
        display_name="legacy_admin_only",
        collection_name="legacy_collection",
        created_by="usr_admin",
    )
    web_app.collection_name_mapping.update(
        {
            public_kb["collection_original_name"]: public_kb["collection_name"],
            own_kb["collection_original_name"]: own_kb["collection_name"],
            other_kb["collection_original_name"]: other_kb["collection_name"],
            legacy_kb["collection_original_name"]: legacy_kb["collection_name"],
            "unregistered_global": "unregistered_global",
        }
    )
    audit_records = [
        {"actor_user_id": user["id"], "kb_id": own_kb["id"], "status": "success"},
        {"actor_user_id": other_user["id"], "kb_id": other_kb["id"], "status": "success"},
        {"tenant_id": "legacy_tenant", "collection_name": "legacy_collection", "status": "success"},
    ]
    audit_file = upload_root / "upload_manifest.jsonl"
    audit_file.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in audit_records) + "\n",
        encoding="utf-8",
    )
    _login(client, "reviewer", "user-secret")

    mappings_response = client.get("/api/rag/mappings")
    audit_response = client.get("/api/uploads/audit")

    assert mappings_response.status_code == 200
    normalized_names = {
        item["normalized_name"]
        for item in mappings_response.json()["mappings"]
    }
    assert normalized_names == {public_kb["collection_name"], own_kb["collection_name"]}
    assert audit_response.status_code == 200
    assert audit_response.json()["records"] == [
        {"actor_user_id": user["id"], "kb_id": own_kb["id"], "status": "success"}
    ]


def test_unmapped_legacy_collection_requests_return_410_without_touching_rag(tmp_path, monkeypatch):
    """不能安全映射到 kb_id 的 legacy 资料库请求应被拒绝且不触发 RAG。"""
    client, _ = _configure_legacy_test_app(tmp_path, monkeypatch)
    _create_regular_user("reviewer")
    rag_calls: list[str] = []

    def fail_if_touched(collection_name: str):
        rag_calls.append(collection_name)
        raise AssertionError("未授权 legacy collection 不应触发 RAG 运行时")

    monkeypatch.setattr(web_app, "get_rag_agent", fail_if_touched)
    _login(client, "reviewer", "user-secret")

    responses = [
        client.get("/api/rag/documents/unregistered_collection"),
        client.get("/api/rag/document/unregistered_collection/doc_1"),
        client.delete("/api/rag/document/unregistered_collection/doc_1"),
        client.request(
            "DELETE",
            "/api/rag/documents/batch",
            json={"collection_name": "unregistered_collection", "doc_ids": ["doc_1"]},
        ),
        client.delete("/api/rag/clear/unregistered_collection"),
        client.delete("/api/rag/collection/unregistered_collection"),
    ]

    assert [response.status_code for response in responses] == [410, 410, 410, 410, 410, 410]
    assert rag_calls == []


def test_registered_legacy_collection_operations_follow_kb_permissions(tmp_path, monkeypatch):
    """legacy 文档操作应复用 registry 权限矩阵。"""
    client, _ = _configure_legacy_test_app(tmp_path, monkeypatch)
    _create_regular_user("reviewer")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="public_law",
        created_by="usr_admin",
    )
    _login(client, "reviewer", "user-secret")

    read_response = client.get(f"/api/rag/documents/{public_kb['collection_name']}")
    clear_response = client.delete(f"/api/rag/clear/{public_kb['collection_name']}")

    assert read_response.status_code == 200
    assert clear_response.status_code == 403


def test_history_and_memory_use_current_user_scope(tmp_path, monkeypatch):
    """history 与 memory 接口不应复用全局原始 session_id。"""
    client, _ = _configure_legacy_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    scoped_session_ids: list[str] = []

    def fake_memory_agent(session_id: str):
        scoped_session_ids.append(session_id)
        return _FakeMemoryAgent()

    monkeypatch.setattr(web_app, "get_memory_agent", fake_memory_agent)
    web_app.session_histories["shared_session"] = [
        {"role": "assistant", "content": "不应泄漏的全局历史"}
    ]
    _login(client, "reviewer", "user-secret")

    history_response = client.get("/api/history/shared_session")
    memory_response = client.post(
        "/api/memory/store",
        json={
            "content": "记忆内容",
            "memory_type": "short_term",
            "importance": 3,
            "session_id": "shared_session",
        },
    )

    assert history_response.status_code == 200
    assert history_response.json()["messages"] == []
    assert memory_response.status_code == 200
    assert scoped_session_ids == [f"{user['id']}__shared_session"]

"""RAG 资料库删除接口测试。"""

from pathlib import Path
from urllib.parse import quote

import chromadb
from chromadb.config import Settings as ChromaSettings
from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.kb import registry


def _create_chroma_client(vector_db_path: str):
    """创建指向测试目录的 ChromaDB 客户端。"""
    return chromadb.PersistentClient(
        path=vector_db_path,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )


def _reset_rag_state(vector_db_path: str, monkeypatch):
    """将 RAG 测试状态隔离到临时向量库目录。"""
    monkeypatch.setattr(web_app.settings, "vector_db_path", vector_db_path)
    monkeypatch.setattr(
        storage,
        "DEFAULT_AUTH_DB_PATH",
        Path(vector_db_path).parent / "auth" / "app.sqlite3",
    )
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    web_app.rag_agents.clear()
    web_app.collection_name_mapping.clear()


def _login_admin(client: TestClient):
    """登录管理员，让 legacy RAG 删除接口通过默认认证边界。"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )
    assert response.status_code == 200


def test_delete_collection_removes_collection_from_list(tmp_path, monkeypatch):
    """删除资料库后，该资料库不应再出现在资料库列表中。"""
    vector_db_path = str(tmp_path / "chroma")
    _reset_rag_state(vector_db_path, monkeypatch)

    chroma_client = _create_chroma_client(vector_db_path)
    chroma_client.create_collection(
        name="delete_me",
        metadata={"hnsw:space": "cosine"},
    )

    client = TestClient(web_app.app)
    _login_admin(client)
    registry.register_legacy_knowledge_base(
        display_name="delete_me",
        collection_name="delete_me",
        created_by="usr_admin",
    )

    before_response = client.get("/api/rag/collections")
    assert before_response.status_code == 200
    before_data = before_response.json()
    assert any(
        item["collection_name"] == "delete_me"
        for item in before_data["collections"]
    )

    delete_response = client.delete("/api/rag/collection/delete_me")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    after_response = client.get("/api/rag/collections")
    assert after_response.status_code == 200
    after_data = after_response.json()
    assert all(
        item["collection_name"] != "delete_me"
        for item in after_data["collections"]
    )


def test_delete_unregistered_collection_returns_410_without_creating_mapping(tmp_path, monkeypatch):
    """删除未登记的 legacy 资料库应返回 410，且不能写入新的名称映射。"""
    vector_db_path = str(tmp_path / "chroma")
    _reset_rag_state(vector_db_path, monkeypatch)
    _create_chroma_client(vector_db_path)

    client = TestClient(web_app.app)
    _login_admin(client)

    response = client.delete(f"/api/rag/collection/{quote('不存在的资料库')}")

    assert response.status_code == 410
    assert web_app.collection_name_mapping == {}


def test_delete_collection_by_original_chinese_name_cleans_mapping(tmp_path, monkeypatch):
    """使用中文原始资料库名删除时，应删除系统集合并清理映射。"""
    vector_db_path = str(tmp_path / "chroma")
    _reset_rag_state(vector_db_path, monkeypatch)

    original_name = "法规案例库"
    normalized_name = web_app.build_normalized_collection_name(original_name)
    web_app.collection_name_mapping[original_name] = normalized_name
    web_app.rag_agents[normalized_name] = object()

    chroma_client = _create_chroma_client(vector_db_path)
    chroma_client.create_collection(
        name=normalized_name,
        metadata={
            "hnsw:space": "cosine",
            "original_name": original_name,
        },
    )

    client = TestClient(web_app.app)
    _login_admin(client)
    registry.register_legacy_knowledge_base(
        display_name=original_name,
        collection_name=normalized_name,
        collection_original_name=original_name,
        created_by="usr_admin",
    )

    response = client.delete(f"/api/rag/collection/{quote(original_name)}")

    assert response.status_code == 200
    data = response.json()
    assert data["collection_name"] == normalized_name
    assert data["original_name"] == original_name
    assert normalized_name not in web_app.rag_agents
    assert original_name not in web_app.collection_name_mapping
    assert normalized_name not in {
        collection.name
        for collection in chroma_client.list_collections()
    }


def test_remove_collection_runtime_state_cleans_agent_and_all_stale_mappings():
    """删除 collection 后应清理同一系统集合对应的所有运行态缓存。"""
    web_app.rag_agents.clear()
    web_app.collection_name_mapping.clear()
    web_app.rag_agents["kb_normalized"] = object()
    web_app.collection_name_mapping["原始名称"] = "kb_normalized"
    web_app.collection_name_mapping["tenant_a__原始名称"] = "kb_normalized"

    web_app._remove_collection_runtime_state("kb_normalized", "原始名称")

    assert "kb_normalized" not in web_app.rag_agents
    assert web_app.collection_name_mapping == {}


def test_delete_tenant_collection_does_not_delete_default_collection(tmp_path, monkeypatch):
    """非默认租户删除同名资料库时，不应误删默认租户资料库。"""
    vector_db_path = str(tmp_path / "chroma")
    _reset_rag_state(vector_db_path, monkeypatch)

    chroma_client = _create_chroma_client(vector_db_path)
    chroma_client.create_collection(
        name="shared_kb",
        metadata={"hnsw:space": "cosine"},
    )
    chroma_client.create_collection(
        name="tenant_a__shared_kb",
        metadata={
            "hnsw:space": "cosine",
            "original_name": "tenant_a__shared_kb",
        },
    )

    client = TestClient(web_app.app)
    _login_admin(client)
    registry.register_legacy_knowledge_base(
        display_name="shared_kb",
        collection_name="tenant_a__shared_kb",
        collection_original_name="tenant_a__shared_kb",
        created_by="usr_admin",
    )

    response = client.delete("/api/rag/collection/shared_kb?tenant_id=tenant_a")

    assert response.status_code == 200
    remaining_collection_names = {
        collection.name
        for collection in chroma_client.list_collections()
    }
    assert "shared_kb" in remaining_collection_names
    assert "tenant_a__shared_kb" not in remaining_collection_names

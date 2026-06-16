"""知识库 kb_id 文档浏览和删除 API 测试。"""

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.kb import registry


class _FakeRAGAgent:
    """避免测试触发真实向量库和嵌入服务。"""

    def __init__(self, collection_name: str, documents: list[dict], calls: list[dict]):
        self.collection_name = collection_name
        self.documents = {document["id"]: document for document in documents}
        self.calls = calls

    def list_documents(self, limit=None, offset=None):
        self.calls.append(
            {
                "method": "list_documents",
                "collection_name": self.collection_name,
                "limit": limit,
                "offset": offset,
            }
        )
        documents = list(self.documents.values())
        start = offset or 0
        end = None if limit is None else start + limit
        return documents[start:end]

    def get_document_count(self) -> int:
        return len(self.documents)

    def get_document_by_id(self, doc_id: str):
        self.calls.append(
            {
                "method": "get_document_by_id",
                "collection_name": self.collection_name,
                "doc_id": doc_id,
            }
        )
        return self.documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        self.calls.append(
            {
                "method": "delete_document",
                "collection_name": self.collection_name,
                "doc_id": doc_id,
            }
        )
        return self.documents.pop(doc_id, None) is not None

    def batch_delete_documents(self, doc_ids: list[str]):
        self.calls.append(
            {
                "method": "batch_delete_documents",
                "collection_name": self.collection_name,
                "doc_ids": doc_ids,
            }
        )
        failed_ids = []
        success_count = 0
        for doc_id in doc_ids:
            if self.documents.pop(doc_id, None) is None:
                failed_ids.append(doc_id)
            else:
                success_count += 1
        return success_count, failed_ids

    def clear_knowledge_base(self):
        self.calls.append(
            {
                "method": "clear_knowledge_base",
                "collection_name": self.collection_name,
            }
        )
        self.documents.clear()

    def delete_knowledge_base(self):
        self.calls.append(
            {
                "method": "delete_knowledge_base",
                "collection_name": self.collection_name,
            }
        )
        self.documents.clear()


def _configure_kb_documents_test_app(tmp_path, monkeypatch):
    """将知识库文档 API 测试隔离到临时认证库和假 RAG Agent。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    agents: dict[str, _FakeRAGAgent] = {}
    rag_calls: list[dict] = []

    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    web_app.rag_agents.clear()
    web_app.collection_name_mapping.clear()

    def get_fake_agent(collection_name: str):
        return agents.setdefault(
            collection_name,
            _FakeRAGAgent(collection_name, [], rag_calls),
        )

    monkeypatch.setattr(web_app, "get_rag_agent", get_fake_agent)
    return TestClient(web_app.app), agents, rag_calls


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


def _seed_agent(
    agents: dict[str, _FakeRAGAgent],
    collection_name: str,
    rag_calls: list[dict],
):
    """写入假文档。"""
    documents = [
        {
            "id": "doc_1",
            "text": "第一份合同模板",
            "metadata": {"source": "contract-a.docx"},
        },
        {
            "id": "doc_2",
            "text": "第二份合同模板",
            "metadata": {"source": "contract-b.docx"},
        },
    ]
    agents[collection_name] = _FakeRAGAgent(collection_name, documents, rag_calls)
    return agents[collection_name]


def test_user_can_list_get_delete_batch_and_clear_own_documents(tmp_path, monkeypatch):
    """普通用户应只能浏览和删除自己的用户知识库资料。"""
    client, agents, rag_calls = _configure_kb_documents_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="my_docs",
        created_by=user["id"],
    )
    _seed_agent(agents, user_kb["collection_name"], rag_calls)
    _login(client, "reviewer", "user-secret")

    list_response = client.get(f"/api/kb/collections/{user_kb['id']}/documents?limit=1&offset=1")
    get_response = client.get(f"/api/kb/collections/{user_kb['id']}/documents/doc_1")
    delete_response = client.delete(f"/api/kb/collections/{user_kb['id']}/documents/doc_1")
    batch_response = client.request(
        "DELETE",
        f"/api/kb/collections/{user_kb['id']}/documents/batch",
        json={"doc_ids": ["doc_2", "missing_doc"]},
    )
    clear_response = client.delete(f"/api/kb/collections/{user_kb['id']}/clear")

    assert list_response.status_code == 200
    assert list_response.json()["documents"][0]["id"] == "doc_2"
    assert list_response.json()["total_count"] == 2
    assert get_response.status_code == 200
    assert get_response.json()["document"]["id"] == "doc_1"
    assert delete_response.status_code == 200
    assert delete_response.json()["remaining_count"] == 1
    assert batch_response.status_code == 200
    assert batch_response.json()["success_count"] == 1
    assert batch_response.json()["failed_ids"] == ["missing_doc"]
    assert clear_response.status_code == 200
    assert clear_response.json()["remaining_count"] == 0
    assert [call["method"] for call in rag_calls] == [
        "list_documents",
        "get_document_by_id",
        "delete_document",
        "batch_delete_documents",
        "clear_knowledge_base",
    ]


def test_regular_user_cannot_delete_public_documents(tmp_path, monkeypatch):
    """普通用户可浏览公共库资料，但不能删除或清空公共库。"""
    client, agents, rag_calls = _configure_kb_documents_test_app(tmp_path, monkeypatch)
    _create_regular_user("reviewer")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="public_law",
        created_by="usr_admin",
    )
    _seed_agent(agents, public_kb["collection_name"], rag_calls)
    _login(client, "reviewer", "user-secret")

    list_response = client.get(f"/api/kb/collections/{public_kb['id']}/documents")
    delete_response = client.delete(f"/api/kb/collections/{public_kb['id']}/documents/doc_1")
    batch_response = client.request(
        "DELETE",
        f"/api/kb/collections/{public_kb['id']}/documents/batch",
        json={"doc_ids": ["doc_1"]},
    )
    clear_response = client.delete(f"/api/kb/collections/{public_kb['id']}/clear")

    assert list_response.status_code == 200
    assert delete_response.status_code == 403
    assert batch_response.status_code == 403
    assert clear_response.status_code == 403
    assert [call["method"] for call in rag_calls] == ["list_documents"]


def test_admin_can_clear_public_documents(tmp_path, monkeypatch):
    """管理员应可清空公共知识库资料。"""
    client, agents, rag_calls = _configure_kb_documents_test_app(tmp_path, monkeypatch)
    admin = _login(client)
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="public_law",
        created_by=admin["id"],
    )
    _seed_agent(agents, public_kb["collection_name"], rag_calls)

    response = client.delete(f"/api/kb/collections/{public_kb['id']}/clear")

    assert response.status_code == 200
    assert response.json()["remaining_count"] == 0
    assert rag_calls == [
        {
            "method": "clear_knowledge_base",
            "collection_name": public_kb["collection_name"],
        }
    ]


def test_delete_kb_collection_deletes_agent_collection_and_clears_runtime_cache(tmp_path, monkeypatch):
    """删除知识库应删除底层 collection、软删除元数据并清理运行态缓存。"""
    client, agents, rag_calls = _configure_kb_documents_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="my_docs",
        created_by=user["id"],
    )
    _seed_agent(agents, user_kb["collection_name"], rag_calls)
    web_app.rag_agents[user_kb["collection_name"]] = agents[user_kb["collection_name"]]
    web_app.collection_name_mapping[user_kb["collection_original_name"]] = user_kb["collection_name"]
    _login(client, "reviewer", "user-secret")

    response = client.delete(f"/api/kb/collections/{user_kb['id']}")
    after_delete_response = client.get(f"/api/kb/collections/{user_kb['id']}")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["deleted"] is True
    assert after_delete_response.status_code == 404
    assert user_kb["collection_name"] not in web_app.rag_agents
    assert user_kb["collection_original_name"] not in web_app.collection_name_mapping
    assert rag_calls == [
        {
            "method": "delete_knowledge_base",
            "collection_name": user_kb["collection_name"],
        }
    ]

"""知识库 kb_id 上传 API 测试。"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.kb import registry


class _FakeRAGAgent:
    """避免测试触发真实向量库和嵌入服务。"""

    def __init__(self, collection_name: str, calls: list[dict]):
        self.collection_name = collection_name
        self.calls = calls
        self.total_documents = 0

    def add_texts(self, texts, metadatas=None) -> int:
        self.calls.append(
            {
                "method": "add_texts",
                "collection_name": self.collection_name,
                "texts": texts,
                "metadatas": metadatas,
            }
        )
        self.total_documents += len(texts)
        return len(texts)

    def add_documents_from_file(self, file_path: str, show_progress: bool = True) -> int:
        self.calls.append(
            {
                "method": "add_documents_from_file",
                "collection_name": self.collection_name,
                "file_path": file_path,
                "show_progress": show_progress,
            }
        )
        self.total_documents += 2
        return 2

    def get_document_count(self) -> int:
        return self.total_documents


def _configure_kb_upload_test_app(tmp_path, monkeypatch):
    """将知识库上传 API 测试隔离到临时认证库和上传根目录。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    upload_root = tmp_path / "uploads"
    rag_calls: list[dict] = []

    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    monkeypatch.setattr(web_app.settings, "upload_root_path", str(upload_root))
    monkeypatch.setattr(
        web_app,
        "get_rag_agent",
        lambda collection_name: _FakeRAGAgent(collection_name, rag_calls),
    )
    return TestClient(web_app.app), upload_root, rag_calls


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


def test_user_can_upload_texts_to_own_user_collection(tmp_path, monkeypatch):
    """普通用户应可向自己的用户知识库写入文本。"""
    client, _, rag_calls = _configure_kb_upload_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="我的合同模板",
        created_by=user["id"],
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        f"/api/kb/collections/{user_kb['id']}/texts",
        json={
            "texts": ["第一条合同模板", "第二条合同模板"],
            "metadatas": [{"source": "a"}, {"source": "b"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["kb_id"] == user_kb["id"]
    assert body["collection_name"] == user_kb["collection_name"]
    assert body["chunks_added"] == 2
    assert rag_calls == [
        {
            "method": "add_texts",
            "collection_name": user_kb["collection_name"],
            "texts": ["第一条合同模板", "第二条合同模板"],
            "metadatas": [{"source": "a"}, {"source": "b"}],
        }
    ]


def test_regular_user_cannot_write_public_collection(tmp_path, monkeypatch):
    """普通用户不能向公共知识库写入文本或文件。"""
    client, _, rag_calls = _configure_kb_upload_test_app(tmp_path, monkeypatch)
    _create_regular_user("reviewer")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="法规案例库",
        created_by="usr_admin",
    )
    _login(client, "reviewer", "user-secret")

    text_response = client.post(
        f"/api/kb/collections/{public_kb['id']}/texts",
        json={"texts": ["普通用户不能写公共库"]},
    )
    upload_response = client.post(
        f"/api/kb/collections/{public_kb['id']}/upload",
        files={"file": ("risk.txt", b"risk content", "text/plain")},
    )

    assert text_response.status_code == 403
    assert upload_response.status_code == 403
    assert rag_calls == []


def test_admin_can_upload_texts_and_files_to_public_collection(tmp_path, monkeypatch):
    """管理员应可向公共知识库写入文本并上传文件。"""
    client, upload_root, rag_calls = _configure_kb_upload_test_app(tmp_path, monkeypatch)
    admin = _login(client)
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="法规案例库",
        created_by=admin["id"],
    )

    text_response = client.post(
        f"/api/kb/collections/{public_kb['id']}/texts",
        json={"texts": ["公共法规条款"]},
    )
    upload_response = client.post(
        f"/api/kb/collections/{public_kb['id']}/upload",
        files={"file": ("law.txt", b"public law", "text/plain")},
    )

    assert text_response.status_code == 200
    assert upload_response.status_code == 200
    upload_body = upload_response.json()
    assert upload_body["kb_id"] == public_kb["id"]
    assert upload_body["collection_name"] == public_kb["collection_name"]
    assert Path(upload_body["stored_file_path"]).is_file()
    assert Path(upload_body["stored_file_path"]).is_relative_to(
        upload_root / "public" / public_kb["id"] / "rag"
    )
    assert [call["method"] for call in rag_calls] == ["add_texts", "add_documents_from_file"]
    assert rag_calls[0]["collection_name"] == public_kb["collection_name"]
    assert rag_calls[1]["collection_name"] == public_kb["collection_name"]


def test_user_uploaded_files_are_saved_under_user_and_kb_scope(tmp_path, monkeypatch):
    """用户知识库上传文件应保存到 users/{user_id}/rag/{kb_id} 作用域。"""
    client, upload_root, rag_calls = _configure_kb_upload_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="我的合同模板",
        created_by=user["id"],
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        f"/api/kb/collections/{user_kb['id']}/upload",
        files={"file": ("template.txt", b"user template", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    stored_path = Path(body["stored_file_path"])
    assert stored_path.is_file()
    assert stored_path.is_relative_to(upload_root / "users" / user["id"] / "rag" / user_kb["id"])
    assert body["file_id"]
    assert body["chunks_added"] == 2
    assert rag_calls == [
        {
            "method": "add_documents_from_file",
            "collection_name": user_kb["collection_name"],
            "file_path": str(stored_path),
            "show_progress": True,
        }
    ]

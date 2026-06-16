"""kb_id 驱动的 RAG 查询 API 测试。"""

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.kb import registry


class _FakeRAGAgent:
    """避免测试触发真实向量库、嵌入服务和 LLM。"""

    def __init__(self, collection_name: str, calls: list[dict]):
        self.collection_name = collection_name
        self.calls = calls

    def query(
        self,
        question: str,
        top_k=None,
        use_history: bool = True,
        optimize_query: bool = True,
        stream: bool = False,
    ):
        self.calls.append(
            {
                "method": "query",
                "collection_name": self.collection_name,
                "question": question,
                "top_k": top_k,
                "use_history": use_history,
                "optimize_query": optimize_query,
                "stream": stream,
            }
        )
        if stream:
            return iter(["第一段", "第二段"])
        return f"授权回答: {question}"


def _configure_rag_query_test_app(tmp_path, monkeypatch):
    """将 RAG 查询测试隔离到临时认证库和假 RAG Agent。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    rag_calls: list[dict] = []

    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    web_app.rag_agents.clear()
    web_app.collection_name_mapping.clear()
    monkeypatch.setattr(
        web_app,
        "get_rag_agent",
        lambda collection_name: _FakeRAGAgent(collection_name, rag_calls),
    )
    return TestClient(web_app.app), rag_calls


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


def test_rag_query_uses_authorized_kb_id(tmp_path, monkeypatch):
    """非流式查询应使用授权 kb_id 对应的 collection。"""
    client, rag_calls = _configure_rag_query_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="my_templates",
        created_by=user["id"],
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/rag/query",
        json={
            "question": "请总结合同风险",
            "kb_id": user_kb["id"],
            "collection_name": "forged_collection",
            "tenant_id": "forged_tenant",
            "top_k": 3,
            "use_history": False,
            "optimize_query": False,
            "session_id": "contract_review",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "授权回答: 请总结合同风险"
    assert body["kb_id"] == user_kb["id"]
    assert body["collection_name"] == user_kb["collection_name"]
    assert body["display_name"] == user_kb["display_name"]
    assert body["scope"] == "user"
    assert body["session_id"] == "contract_review"
    assert rag_calls == [
        {
            "method": "query",
            "collection_name": user_kb["collection_name"],
            "question": "请总结合同风险",
            "top_k": 3,
            "use_history": False,
            "optimize_query": False,
            "stream": False,
        }
    ]


def test_rag_query_stream_uses_authorized_kb_id(tmp_path, monkeypatch):
    """流式查询也应使用授权 kb_id 对应的 collection。"""
    client, rag_calls = _configure_rag_query_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="public_law",
        created_by="usr_admin",
    )
    _login(client, "reviewer", "user-secret")

    with client.stream(
        "POST",
        "/api/rag/query/stream",
        json={
            "question": "查询公共法规",
            "kb_id": public_kb["id"],
            "collection_name": "forged_collection",
            "tenant_id": "forged_tenant",
            "top_k": 2,
        },
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert '"content": "第一段"' in body
    assert '"content": "第二段"' in body
    assert '"done": true' in body
    assert rag_calls == [
        {
            "method": "query",
            "collection_name": public_kb["collection_name"],
            "question": "查询公共法规",
            "top_k": 2,
            "use_history": True,
            "optimize_query": True,
            "stream": True,
        }
    ]


def test_unauthorized_or_missing_kb_id_does_not_touch_rag(tmp_path, monkeypatch):
    """无权限或不存在 kb_id 时不得启动 RAG 或自动创建 collection。"""
    client, _ = _configure_rag_query_test_app(tmp_path, monkeypatch)
    owner = _create_regular_user("owner", "owner-secret")
    _create_regular_user("reviewer", "user-secret")
    owner_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=owner["id"],
        display_name="owner_private",
        created_by=owner["id"],
    )
    rag_calls: list[str] = []

    def fail_if_touched(collection_name: str):
        rag_calls.append(collection_name)
        raise AssertionError("无权限或不存在 kb_id 不应触发 RAG 运行时")

    monkeypatch.setattr(web_app, "get_rag_agent", fail_if_touched)
    _login(client, "reviewer", "user-secret")

    forbidden_response = client.post(
        "/api/rag/query",
        json={"question": "不能访问", "kb_id": owner_kb["id"]},
    )
    missing_response = client.post(
        "/api/rag/query",
        json={"question": "不存在", "kb_id": "kb_missing"},
    )
    stream_response = client.post(
        "/api/rag/query/stream",
        json={"question": "流式也不能访问", "kb_id": owner_kb["id"]},
    )

    assert forbidden_response.status_code == 404
    assert missing_response.status_code == 404
    assert stream_response.status_code == 404
    assert rag_calls == []

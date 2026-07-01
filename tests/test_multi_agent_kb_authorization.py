"""多智能体知识库授权接入测试。"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.kb import registry


class _FakeCompositeRAGRetriever:
    """记录多知识库来源，避免触发真实检索。"""

    def __init__(self, knowledge_bases, agent_factory=None, **kwargs):
        self.knowledge_bases = list(knowledge_bases)
        self.agent_factory = agent_factory
        self.kwargs = kwargs


class _FakeCollaboration:
    """避免测试触发真实多智能体 LLM 调用。"""

    instances: list["_FakeCollaboration"] = []

    def __init__(
        self,
        llm_client,
        mode,
        verbose=True,
        max_rounds=5,
        rag_agent=None,
        execution_policy=None,
        lang="zh",
    ):
        self.llm_client = llm_client
        self.mode = mode
        self.verbose = verbose
        self.max_rounds = max_rounds
        self.rag_agent = rag_agent
        self.execution_policy = execution_policy
        self.lang = lang
        self.agents = []
        self.collaborate_calls = []
        self.__class__.instances.append(self)

    def register_agents(self, agents):
        self.agents = agents

    def collaborate(self, input_text, context=None):
        self.collaborate_calls.append({"input_text": input_text, "context": context})
        return SimpleNamespace(
            success=True,
            final_output="合同审查完成",
            agent_contributions={},
            messages=[],
            execution_time=0.01,
            error_message="",
            metadata={},
        )


class _FakeLLMClient:
    """记录 LLM 客户端是否被初始化。"""

    calls: list[str] = []

    def __init__(self):
        self.__class__.calls.append("init")


def _configure_multi_agent_kb_test_app(tmp_path, monkeypatch):
    """将多智能体知识库测试隔离到临时数据库和假运行时。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    rag_calls: list[str] = []
    _FakeCollaboration.instances.clear()
    _FakeLLMClient.calls.clear()

    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    web_app.rag_agents.clear()
    web_app.collection_name_mapping.clear()
    monkeypatch.setattr(web_app, "GiteeAIClient", _FakeLLMClient)
    monkeypatch.setattr(web_app, "MultiAgentCollaboration", _FakeCollaboration)
    monkeypatch.setattr(web_app, "CompositeRAGRetriever", _FakeCompositeRAGRetriever, raising=False)
    monkeypatch.setattr(
        web_app,
        "get_rag_agent",
        lambda collection_name: rag_calls.append(collection_name)
        or SimpleNamespace(collection_name=collection_name),
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


def _agent_names(agents) -> list[str]:
    """提取协作运行时实际注册的 Agent 名称。"""
    return [agent.name for agent in agents]


def test_multi_agent_collaborate_uses_authorized_kb_ids_and_public_sources(tmp_path, monkeypatch):
    """非流式协作应使用授权知识库并在 metadata 标注来源。"""
    client, rag_calls = _configure_multi_agent_kb_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    other = _create_regular_user("other")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="公共法规库",
        created_by="usr_admin",
    )
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="我的合同库",
        created_by=user["id"],
    )
    registry.create_knowledge_base(
        scope="user",
        owner_user_id=other["id"],
        display_name="他人合同库",
        created_by=other["id"],
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请审查违约责任条款",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "enable_rag": True,
            "knowledge_base_ids": [user_kb["id"]],
            "include_public_knowledge": True,
            "collection_name": "forged_collection",
            "tenant_id": "forged_tenant",
            "context": {"contract_type": "采购合同"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert {item["kb_id"] for item in body["metadata"]["knowledge_bases"]} == {
        public_kb["id"],
        user_kb["id"],
    }
    assert {
        (item["scope"], item["display_name"])
        for item in body["metadata"]["knowledge_bases"]
    } == {
        ("public", "公共法规库"),
        ("user", "我的合同库"),
    }
    assert "tenant_id" not in body["metadata"]
    assert "collection_name" not in body["metadata"]

    collaboration = _FakeCollaboration.instances[-1]
    assert isinstance(collaboration.rag_agent, _FakeCompositeRAGRetriever)
    assert {item["id"] for item in collaboration.rag_agent.knowledge_bases} == {
        public_kb["id"],
        user_kb["id"],
    }
    assert all(call != "forged_collection" for call in rag_calls)
    assert _FakeLLMClient.calls == ["init"]


def test_multi_agent_stream_uses_same_kb_metadata_as_non_stream(tmp_path, monkeypatch):
    """流式协作也应返回授权知识库来源 metadata。"""
    client, _ = _configure_multi_agent_kb_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="公共案例库",
        created_by="usr_admin",
    )
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="我的模板库",
        created_by=user["id"],
    )
    _login(client, "reviewer", "user-secret")

    with client.stream(
        "POST",
        "/api/multi-agent/collaborate/stream",
        json={
            "input_text": "请审查付款条款",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "enable_rag": True,
            "knowledge_base_ids": [user_kb["id"]],
            "include_public_knowledge": True,
            "tenant_id": "forged_tenant",
            "collection_name": "forged_collection",
        },
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert '"type": "team_info"' in body
    assert '"type": "complete"' in body
    assert public_kb["id"] in body
    assert user_kb["id"] in body
    assert "公共案例库" in body
    assert "我的模板库" in body
    assert "forged_tenant" not in body
    assert "forged_collection" not in body


def test_multi_agent_unauthorized_kb_id_does_not_start_runtime(tmp_path, monkeypatch):
    """无权限 kb_id 在流式和非流式接口都不得启动 LLM 或 RAG。"""
    client, rag_calls = _configure_multi_agent_kb_test_app(tmp_path, monkeypatch)
    owner = _create_regular_user("owner", "owner-secret")
    _create_regular_user("reviewer", "user-secret")
    owner_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=owner["id"],
        display_name="owner_private",
        created_by=owner["id"],
    )
    _login(client, "reviewer", "user-secret")

    non_stream_response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "不能访问",
            "team_type": "legal_contract_review",
            "enable_rag": True,
            "knowledge_base_ids": [owner_kb["id"]],
        },
    )
    stream_response = client.post(
        "/api/multi-agent/collaborate/stream",
        json={
            "input_text": "流式也不能访问",
            "team_type": "legal_contract_review",
            "enable_rag": True,
            "knowledge_base_ids": [owner_kb["id"]],
        },
    )

    assert non_stream_response.status_code == 404
    assert stream_response.status_code == 404
    assert _FakeLLMClient.calls == []
    assert _FakeCollaboration.instances == []
    assert rag_calls == []


def test_selecting_rag_agent_does_not_expand_knowledge_base_visibility(
    tmp_path,
    monkeypatch,
):
    """选择 legal_researcher 只能使用请求内已授权知识库，不应扩大可见范围。"""
    client, rag_calls = _configure_multi_agent_kb_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer", "user-secret")
    other = _create_regular_user("other", "other-secret")
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="公共法规库不应自动加入",
        created_by="usr_admin",
    )
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=user["id"],
        display_name="我的法规库",
        created_by=user["id"],
    )
    other_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id=other["id"],
        display_name="他人法规库",
        created_by=other["id"],
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请检索法律依据",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "legal_task_type": "legal_research",
            "selected_agent_names": ["legal_researcher"],
            "enable_rag": True,
            "knowledge_base_ids": [user_kb["id"]],
            "include_public_knowledge": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert _agent_names(_FakeCollaboration.instances[-1].agents) == [
        "contract_reviewer",
        "legal_researcher",
    ]
    assert [item["kb_id"] for item in body["metadata"]["knowledge_bases"]] == [
        user_kb["id"]
    ]
    assert public_kb["id"] not in {
        item["kb_id"] for item in body["metadata"]["knowledge_bases"]
    }
    assert other_kb["id"] not in {
        item["kb_id"] for item in body["metadata"]["knowledge_bases"]
    }
    assert rag_calls == [user_kb["collection_name"]]
    assert _FakeLLMClient.calls == ["init"]


def test_invalid_legal_task_type_fails_before_rag_llm_or_collaboration(
    tmp_path,
    monkeypatch,
):
    """未知法律任务应在 RAG、LLM 和协作对象初始化前返回 400。"""
    client, rag_calls = _configure_multi_agent_kb_test_app(tmp_path, monkeypatch)
    registry.create_knowledge_base(
        scope="public",
        display_name="公共法规库",
        created_by="usr_admin",
    )
    _login(client)

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请审查合同",
            "team_type": "legal_contract_review",
            "legal_task_type": "unknown_task",
            "enable_rag": True,
            "include_public_knowledge": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_legal_task_type"
    assert _FakeLLMClient.calls == []
    assert _FakeCollaboration.instances == []
    assert rag_calls == []


def test_invalid_stream_legal_agent_name_fails_before_rag_llm_or_collaboration(
    tmp_path,
    monkeypatch,
):
    """流式非法法律 Agent 选择也应在运行时初始化前返回 400。"""
    client, rag_calls = _configure_multi_agent_kb_test_app(tmp_path, monkeypatch)
    registry.create_knowledge_base(
        scope="public",
        display_name="公共案例库",
        created_by="usr_admin",
    )
    _login(client)

    response = client.post(
        "/api/multi-agent/collaborate/stream",
        json={
            "input_text": "请审查合同",
            "team_type": "legal_contract_review",
            "selected_agent_names": ["not_a_legal_agent"],
            "enable_rag": True,
            "include_public_knowledge": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_legal_agent_name"
    assert _FakeLLMClient.calls == []
    assert _FakeCollaboration.instances == []
    assert rag_calls == []

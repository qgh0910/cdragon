"""多智能体动态路由 API 契约测试。"""

import json
import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.agents.multi_agent_collaboration import (
    LegalContractReviewTeam,
)
from src.shuyixiao_agent.auth import storage


def _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch):
    """将多智能体路由 API 测试隔离到临时认证数据库。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    _FakeCollaboration.instances.clear()
    _FakeLLMClient.calls.clear()
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    return TestClient(web_app.app)


def _login(client: TestClient):
    """登录测试管理员，避免 /teams 红灯跑偏为 401。"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )
    assert response.status_code == 200


def _get_teams(client: TestClient) -> dict:
    """获取团队 payload，并先确认认证夹具可用。"""
    response = client.get("/api/multi-agent/teams")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    return data["teams"]


class _FakeCollaboration:
    """记录多智能体运行时调用，避免触发真实 LLM。"""

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
        self.agents = list(agents)

    def collaborate(self, input_text, context=None):
        self.collaborate_calls.append({"input_text": input_text, "context": context})
        return SimpleNamespace(
            success=True,
            final_output="ok",
            agent_contributions={},
            messages=[],
            execution_time=0.01,
            error_message="",
            metadata={"runtime_marker": "fake"},
        )


class _FakeLLMClient:
    """记录 LLM 客户端是否被初始化。"""

    calls: list[str] = []

    def __init__(self):
        self.__class__.calls.append("init")


def _patch_fake_runtime(monkeypatch):
    """替换运行时，避免 API 测试触发真实 LLM。"""
    monkeypatch.setattr(web_app, "GiteeAIClient", _FakeLLMClient)
    monkeypatch.setattr(web_app, "MultiAgentCollaboration", _FakeCollaboration)


def _agent_names(agents) -> list[str]:
    """提取 Agent 名称，便于断言实际注册成员。"""
    return [agent.name for agent in agents]


def _sse_events(body: str) -> list[dict]:
    """解析测试用 SSE data 事件。"""
    return [
        json.loads(block.removeprefix("data: "))
        for block in body.strip().split("\n\n")
        if block.startswith("data: ")
    ]


def _assert_fake_runtime_not_started():
    """断言请求在 LLM 和协作对象初始化前已经失败。"""
    assert _FakeLLMClient.calls == []
    assert _FakeCollaboration.instances == []


LEGAL_LOG_EVENTS = {
    "legal_collaboration_started",
    "legal_collaboration_completed",
    "legal_collaboration_failed",
}
LEGAL_LOG_ALLOWED_EXTRA_KEYS = {
    "event",
    "request_id",
    "user_id",
    "tenant_id",
    "legal_task_type",
    "mode",
    "selection_source",
    "selected_agent_names",
    "status",
    "duration_ms",
    "error_code",
}
LOG_RECORD_STANDARD_KEYS = set(
    logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    ).__dict__
)


def _legal_event_records(caplog) -> list[logging.LogRecord]:
    """提取法律多智能体最小结构化日志事件。"""
    return [
        record
        for record in caplog.records
        if getattr(record, "event", None) in LEGAL_LOG_EVENTS
    ]


def _log_record_extras(record: logging.LogRecord) -> dict:
    """返回 logging extra 写入的字段，排除标准 LogRecord 字段。"""
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in LOG_RECORD_STANDARD_KEYS
        and key not in {"message", "asctime"}
    }


def _assert_legal_log_record_is_minimal(record: logging.LogRecord):
    """法律协作日志只能包含最终方案允许的安全字段。"""
    extras = _log_record_extras(record)
    assert set(extras) <= LEGAL_LOG_ALLOWED_EXTRA_KEYS
    assert extras["request_id"].startswith("mac_")
    assert extras["user_id"]
    assert extras["tenant_id"] == "default"
    assert extras["legal_task_type"] == "revision_suggestions"
    assert extras["mode"] == "hierarchical"
    assert extras["selection_source"] == "user_override"
    assert list(extras["selected_agent_names"]) == [
        "contract_reviewer",
        "drafting_specialist",
    ]


SENSITIVE_RUNTIME_LEAKS = [
    "/private/secret",
    "api-key",
    "sk-test-secret",
    "合同正文敏感片段",
]
SENSITIVE_RUNTIME_ERROR = (
    "boom /private/secret with api-key sk-test-secret and 合同正文敏感片段"
)


class _FailingCollaboration(_FakeCollaboration):
    """模拟运行时异常，异常消息包含不应外泄的敏感内容。"""

    def collaborate(self, input_text, context=None):
        self.collaborate_calls.append({"input_text": input_text, "context": context})
        raise RuntimeError(SENSITIVE_RUNTIME_ERROR)


def _patch_failing_runtime(monkeypatch):
    """替换为会抛出敏感异常的协作运行时。"""
    monkeypatch.setattr(web_app, "GiteeAIClient", _FakeLLMClient)
    monkeypatch.setattr(web_app, "MultiAgentCollaboration", _FailingCollaboration)


def _legal_revision_payload() -> dict:
    """返回触发 user_override 的法律协作请求。"""
    return {
        "input_text": "请给出修改建议",
        "team_type": "legal_contract_review",
        "mode": "hierarchical",
        "legal_task_type": "revision_suggestions",
        "selected_agent_names": ["drafting_specialist"],
        "tenant_id": "default",
    }


def _assert_no_sensitive_runtime_values(value):
    """断言响应或日志序列化后不含运行时原始异常敏感片段。"""
    serialized = json.dumps(value, ensure_ascii=False, default=str)
    for leak in SENSITIVE_RUNTIME_LEAKS:
        assert leak not in serialized


@pytest.mark.parametrize(
    "selected_agent_names",
    [
        ["a" * 65],
        ["contract_reviewer"] * 21,
        ["contract_reviewer", 123],
    ],
)
def test_multi_agent_request_rejects_invalid_selected_agent_names_shape(
    selected_agent_names,
):
    """法律 Agent 选择字段应由 Pydantic 形状约束拦截为 422。"""
    with pytest.raises(ValidationError) as exc_info:
        web_app.MultiAgentCollaborationRequest.model_validate(
            {
                "input_text": "请审查合同",
                "team_type": "legal_contract_review",
                "selected_agent_names": selected_agent_names,
            }
        )

    errors = exc_info.value.errors()
    assert errors
    assert all(error["loc"][0] == "selected_agent_names" for error in errors)


def test_legal_context_over_one_mib_returns_413_before_runtime(
    tmp_path,
    monkeypatch,
):
    """法律 context 原始 UTF-8 JSON 超过 1 MiB 时应在运行时前返回安全错误。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请审查合同",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "context": {"contract_text": "法" * (1024 * 1024)},
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "legal_context_too_large"


@pytest.mark.parametrize(
    ("endpoint", "payload", "expected_status", "expected_code"),
    [
        (
            "/api/multi-agent/collaborate",
            {"legal_task_type": "   "},
            400,
            "invalid_legal_task_type",
        ),
        (
            "/api/multi-agent/collaborate/stream",
            {"legal_task_type": "   "},
            400,
            "invalid_legal_task_type",
        ),
        (
            "/api/multi-agent/collaborate",
            {"selected_agent_names": ["   "]},
            400,
            "invalid_legal_agent_name",
        ),
        (
            "/api/multi-agent/collaborate/stream",
            {"selected_agent_names": ["not_a_legal_agent"]},
            400,
            "invalid_legal_agent_name",
        ),
        (
            "/api/multi-agent/collaborate",
            {"selected_agent_names": ["contract_reviewer"] * 21},
            422,
            None,
        ),
        (
            "/api/multi-agent/collaborate/stream",
            {"selected_agent_names": ["a" * 65]},
            422,
            None,
        ),
        (
            "/api/multi-agent/collaborate",
            {"selected_agent_names": ["contract_reviewer", 123]},
            422,
            None,
        ),
        (
            "/api/multi-agent/collaborate/stream",
            {"legal_task_type": 123},
            422,
            None,
        ),
        (
            "/api/multi-agent/collaborate",
            {
                "context": {
                    "contract_structure_summary": {
                        "key_clause_summary": [
                            {
                                "source_refs": [
                                    {"page_number": {"too": "deep"}}
                                ]
                            }
                        ]
                    }
                }
            },
            422,
            "invalid_legal_context_field",
        ),
        (
            "/api/multi-agent/collaborate/stream",
            {"context": {"contract_text": "法" * (1024 * 1024)}},
            413,
            "legal_context_too_large",
        ),
    ],
)
def test_legal_4xx_requests_fail_before_runtime_initialization(
    tmp_path,
    monkeypatch,
    endpoint,
    payload,
    expected_status,
    expected_code,
):
    """普通和 SSE 的可预检查 4xx 都不得初始化 LLM 或协作运行时。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    request_payload = {
        "input_text": "请审查合同",
        "team_type": "legal_contract_review",
        "mode": "hierarchical",
    }
    request_payload.update(payload)

    response = client.post(endpoint, json=request_payload)

    assert response.status_code == expected_status
    if expected_code:
        assert response.json()["detail"]["code"] == expected_code
    _assert_fake_runtime_not_started()


def test_legal_collaborate_defaults_to_four_selected_agents_and_metadata(
    tmp_path,
    monkeypatch,
):
    """默认法律请求应只注册模板四人，并返回权威选择 metadata。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请审查合同",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "context": {"contract_type": "采购合同"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert _agent_names(_FakeCollaboration.instances[-1].agents) == [
        "contract_reviewer",
        "clause_risk_analyzer",
        "legal_researcher",
        "compliance_checker",
    ]
    assert (
        _FakeCollaboration.instances[-1].collaborate_calls[-1]["context"][
            "legal_task_type"
        ]
        == "contract_review"
    )
    assert _FakeCollaboration.instances[-1].execution_policy is not None
    assert body["metadata"]["agent_selection"] == {
        "team_type": "legal_contract_review",
        "legal_task_type": "contract_review",
        "selection_source": "template_default",
        "selected_agent_names": [
            "contract_reviewer",
            "clause_risk_analyzer",
            "legal_researcher",
            "compliance_checker",
        ],
        "missing_recommended_agent_names": [],
        "capability_gaps": [],
    }


def test_legal_context_sanitizes_long_filename_clause_refs_and_task_type(
    tmp_path,
    monkeypatch,
):
    """法律 context 应清洗文件名、条款引用路径，并以服务端任务类型覆盖客户端伪造值。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    long_filename = "/private/uploads/" + ("合同文件" * 120) + ".docx\x00"
    long_clause_title = "付款条款" * 120
    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请给出修改建议",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "legal_task_type": "revision_suggestions",
            "context": {
                "legal_task_type": "forged_task",
                "uploaded_file_name": long_filename,
                "clause_refs": [
                    {
                        "clause_id": "C-001",
                        "title": long_clause_title,
                        "source_name": "/private/uploads/source.pdf",
                        "file_path": "/private/uploads/source.pdf",
                        "uploaded_file_path": "/private/uploads/source.pdf",
                        "text_preview": "条款原文不应进入受控引用" * 80,
                    }
                    for _ in range(25)
                ],
            },
        },
    )

    assert response.status_code == 200
    context = _FakeCollaboration.instances[-1].collaborate_calls[-1]["context"]
    assert context["legal_task_type"] == "revision_suggestions"
    assert context["legal_task_type"] != "forged_task"
    assert len(context["uploaded_file_name"]) <= 255
    assert "/" not in context["uploaded_file_name"]
    assert "\\" not in context["uploaded_file_name"]
    assert "\x00" not in context["uploaded_file_name"]
    assert len(context["clause_refs"]) == 20
    serialized_refs = json.dumps(context["clause_refs"], ensure_ascii=False)
    assert "/private" not in serialized_refs
    assert "file_path" not in serialized_refs
    assert "uploaded_file_path" not in serialized_refs
    assert "text_preview" not in serialized_refs
    assert "条款原文不应进入受控引用" not in serialized_refs
    assert len(context["clause_refs"][0]["title"]) <= 500


def test_legal_collaborate_user_override_reports_capability_gaps(
    tmp_path,
    monkeypatch,
):
    """用户覆盖名单时服务端应补主控，并标注缺失推荐能力。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请给出修改建议",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "legal_task_type": "revision_suggestions",
            "selected_agent_names": ["drafting_specialist"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert _agent_names(_FakeCollaboration.instances[-1].agents) == [
        "contract_reviewer",
        "drafting_specialist",
    ]
    agent_selection = body["metadata"]["agent_selection"]
    assert agent_selection["selection_source"] == "user_override"
    assert agent_selection["selected_agent_names"] == [
        "contract_reviewer",
        "drafting_specialist",
    ]
    assert agent_selection["missing_recommended_agent_names"] == [
        "clause_risk_analyzer",
        "legal_researcher",
    ]
    assert agent_selection["capability_gaps"] == [
        {
            "agent_name": "clause_risk_analyzer",
            "message": "可能缺少条款级风险识别与风险分级",
        },
        {
            "agent_name": "legal_researcher",
            "message": "可能缺少可核验的法律依据与来源",
        },
    ]


def test_legal_collaboration_logs_started_and_completed_minimal_events(
    tmp_path,
    monkeypatch,
    caplog,
):
    """成功法律协作应记录可关联、字段白名单化的 started/completed 事件。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)
    caplog.set_level(logging.INFO)

    response = client.post(
        "/api/multi-agent/collaborate",
        json=_legal_revision_payload(),
    )

    assert response.status_code == 200
    records = _legal_event_records(caplog)
    event_names = [record.event for record in records]
    assert event_names == [
        "legal_collaboration_started",
        "legal_collaboration_completed",
    ]
    assert records[0].request_id == records[1].request_id
    for record in records:
        _assert_legal_log_record_is_minimal(record)
        _assert_no_sensitive_runtime_values(_log_record_extras(record))
    assert records[0].status == "started"
    assert records[1].status == "completed"
    assert isinstance(records[1].duration_ms, int)
    assert records[1].duration_ms >= 0
    assert getattr(records[1], "error_code", None) in {None, ""}


def test_legal_runtime_failure_logs_failed_event_without_raw_exception(
    tmp_path,
    monkeypatch,
    caplog,
):
    """法律运行时异常应记录稳定失败码，日志不得包含原始异常、路径或凭据。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_failing_runtime(monkeypatch)
    caplog.set_level(logging.INFO)

    response = client.post(
        "/api/multi-agent/collaborate",
        json=_legal_revision_payload(),
    )

    assert response.status_code == 500
    records = _legal_event_records(caplog)
    event_names = [record.event for record in records]
    assert event_names == [
        "legal_collaboration_started",
        "legal_collaboration_failed",
    ]
    assert records[0].request_id == records[1].request_id
    failed_record = records[1]
    _assert_legal_log_record_is_minimal(failed_record)
    assert failed_record.status == "failed"
    assert failed_record.error_code == "legal_collaboration_runtime_failed"
    assert isinstance(failed_record.duration_ms, int)
    assert failed_record.duration_ms >= 0
    _assert_no_sensitive_runtime_values(_log_record_extras(failed_record))


def test_legal_runtime_failure_responses_do_not_leak_raw_exception(
    tmp_path,
    monkeypatch,
):
    """普通响应和 SSE error 都不得泄露运行时原始异常中的正文、路径或凭据。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_failing_runtime(monkeypatch)

    response = client.post(
        "/api/multi-agent/collaborate",
        json=_legal_revision_payload(),
    )

    assert response.status_code == 500
    _assert_no_sensitive_runtime_values(response.json())

    with client.stream(
        "POST",
        "/api/multi-agent/collaborate/stream",
        json=_legal_revision_payload(),
    ) as stream_response:
        stream_body = stream_response.read().decode("utf-8")

    assert stream_response.status_code == 200
    events = _sse_events(stream_body)
    error_event = next(event for event in events if event["type"] == "error")
    assert "协作执行失败" in error_event["message"]
    _assert_no_sensitive_runtime_values(error_event)


def test_legal_stream_uses_same_agent_selection_in_team_info_and_complete(
    tmp_path,
    monkeypatch,
):
    """SSE team_info 与 complete 应返回同一份权威选择 metadata。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    with client.stream(
        "POST",
        "/api/multi-agent/collaborate/stream",
        json={
            "input_text": "请给出修改建议",
            "team_type": "legal_contract_review",
            "mode": "hierarchical",
            "legal_task_type": "revision_suggestions",
            "selected_agent_names": ["drafting_specialist"],
        },
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    events = _sse_events(body)
    team_info = next(event for event in events if event["type"] == "team_info")
    complete = next(event for event in events if event["type"] == "complete")
    assert [agent["name"] for agent in team_info["agents"]] == [
        "contract_reviewer",
        "drafting_specialist",
    ]
    assert (
        team_info["metadata"]["agent_selection"]
        == complete["metadata"]["agent_selection"]
    )
    assert team_info["metadata"]["agent_selection"]["selected_agent_names"] == [
        "contract_reviewer",
        "drafting_specialist",
    ]


def test_legal_empty_selection_keeps_only_required_coordinator(
    tmp_path,
    monkeypatch,
):
    """空选择数组表示用户取消所有可选角色，最终只保留主控。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "只做摘要",
            "team_type": "legal_contract_review",
            "legal_task_type": "risk_identification",
            "selected_agent_names": [],
        },
    )

    assert response.status_code == 200
    assert _agent_names(_FakeCollaboration.instances[-1].agents) == [
        "contract_reviewer"
    ]
    agent_selection = response.json()["metadata"]["agent_selection"]
    assert agent_selection["selection_source"] == "user_override"
    assert agent_selection["selected_agent_names"] == ["contract_reviewer"]
    assert agent_selection["missing_recommended_agent_names"] == [
        "clause_risk_analyzer"
    ]


def test_explicit_default_selection_still_reports_template_default(
    tmp_path,
    monkeypatch,
):
    """显式提交默认名单时，选择来源仍应是 template_default。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "请审查合同",
            "team_type": "legal_contract_review",
            "legal_task_type": "legal_research",
            "selected_agent_names": [
                "legal_researcher",
                "contract_reviewer",
            ],
        },
    )

    assert response.status_code == 200
    agent_selection = response.json()["metadata"]["agent_selection"]
    assert agent_selection["selection_source"] == "template_default"
    assert agent_selection["selected_agent_names"] == [
        "contract_reviewer",
        "legal_researcher",
    ]


def test_non_legal_team_ignores_legal_fields_and_keeps_legacy_runtime(
    tmp_path,
    monkeypatch,
):
    """非法律团队携带法律字段时，应保持完整旧团队和原始 context。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)
    _patch_fake_runtime(monkeypatch)
    forged_context = {
        "contract_structure": {"secret": "非法律请求应原样保留"},
        "uploaded_file_path": "/private/contract.txt",
    }

    response = client.post(
        "/api/multi-agent/collaborate",
        json={
            "input_text": "实现一个登录接口",
            "team_type": "software_dev",
            "mode": "hierarchical",
            "legal_task_type": "unknown_task",
            "selected_agent_names": ["not_a_legal_agent"],
            "context": forged_context,
        },
    )

    assert response.status_code == 200
    collaboration = _FakeCollaboration.instances[-1]
    assert len(collaboration.agents) == len(web_app.SoftwareDevelopmentTeam.get_agents())
    assert collaboration.collaborate_calls[-1]["context"] == forged_context
    assert collaboration.execution_policy is None
    assert "agent_selection" not in response.json()["metadata"]


def test_legal_team_agents_are_generated_from_domain_definition(
    tmp_path,
    monkeypatch,
):
    """法律团队成员名称应与领域层注册顺序一致。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)

    teams = _get_teams(client)

    legal_agent_names = [
        agent["name"]
        for agent in teams["legal_contract_review"]["agents"]
    ]
    assert legal_agent_names == [
        agent.name for agent in LegalContractReviewTeam.get_agents()
    ]


def test_legal_team_exposes_selection_policy_from_domain_contract(
    tmp_path,
    monkeypatch,
):
    """法律团队应公开九种任务默认选择、必选主控和能力缺口文案。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)

    teams = _get_teams(client)
    legal_team = teams["legal_contract_review"]
    domain_policy = LegalContractReviewTeam.get_selection_policy()

    assert "selection_policy" in legal_team
    selection_policy = legal_team["selection_policy"]
    assert selection_policy["default_task_type"] == domain_policy.default_task_type
    assert selection_policy["required_agent_names"] == list(
        domain_policy.required_agent_names
    )
    assert set(selection_policy["task_defaults"]) == set(
        domain_policy.task_defaults
    )
    assert len(selection_policy["task_defaults"]) == 9
    assert selection_policy["task_defaults"]["risk_identification"] == [
        "contract_reviewer",
        "clause_risk_analyzer",
    ]
    assert selection_policy["task_defaults"] == {
        task_type: list(agent_names)
        for task_type, agent_names in domain_policy.task_defaults.items()
    }
    assert selection_policy["capability_gaps"] == dict(
        domain_policy.capability_gaps
    )
    assert (
        selection_policy["capability_gaps"]["clause_risk_analyzer"]
        == "可能缺少条款级风险识别与风险分级"
    )
    assert (
        selection_policy["capability_gaps"]["legal_researcher"]
        == "可能缺少可核验的法律依据与来源"
    )


def test_non_legal_teams_do_not_expose_legal_selection_policy(
    tmp_path,
    monkeypatch,
):
    """非法律团队应保持既有结构，不增加法律选择策略字段。"""
    client = _configure_multi_agent_routing_api_test_app(tmp_path, monkeypatch)
    _login(client)

    teams = _get_teams(client)

    non_legal_team_keys = {
        "software_dev",
        "research",
        "content",
        "business",
    }
    assert set(teams) == non_legal_team_keys | {"legal_contract_review"}
    for team_key in non_legal_team_keys:
        assert "selection_policy" not in teams[team_key]

"""多智能体协作 API 请求语言透传测试。"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage


class _FakeCollaboration:
    instances: list["_FakeCollaboration"] = []

    def __init__(
        self,
        llm_client,
        mode,
        verbose=True,
        max_rounds=5,
        rag_agent=None,
        execution_policy=None,
        lang=None,
    ):
        self.lang = lang
        self.agents = []
        self.__class__.instances.append(self)

    def register_agents(self, agents):
        self.agents = list(agents)

    def collaborate(self, input_text, context=None):
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
    pass


@pytest.fixture
def client(tmp_path, monkeypatch):
    _FakeCollaboration.instances.clear()
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    monkeypatch.setattr(web_app, "GiteeAIClient", _FakeLLMClient)
    monkeypatch.setattr(web_app, "MultiAgentCollaboration", _FakeCollaboration)

    test_client = TestClient(web_app.app)
    response = test_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )
    assert response.status_code == 200
    return test_client


def _payload():
    return {
        "input_text": "设计一个合同审查流程",
        "team_type": "software_dev",
        "mode": "sequential",
    }


def test_collaborate_xuserlang_en_propagates_to_collaboration(client):
    response = client.post(
        "/api/multi-agent/collaborate",
        json=_payload(),
        headers={"X-User-Lang": "en"},
    )

    assert response.status_code == 200
    assert _FakeCollaboration.instances[-1].lang == "en"


def test_collaborate_no_header_defaults_zh(client):
    response = client.post("/api/multi-agent/collaborate", json=_payload())

    assert response.status_code == 200
    assert _FakeCollaboration.instances[-1].lang == "zh"


def test_collaborate_stream_xuserlang_ru_propagates(client):
    response = client.post(
        "/api/multi-agent/collaborate/stream",
        json=_payload(),
        headers={"X-User-Lang": "ru"},
    )

    assert response.status_code == 200
    assert _FakeCollaboration.instances[-1].lang == "ru"


def test_collaborate_response_structure_unchanged(client):
    response = client.post("/api/multi-agent/collaborate", json=_payload())

    assert response.status_code == 200
    assert set(response.json()) == {
        "success",
        "final_output",
        "agent_contributions",
        "messages",
        "execution_time",
        "error_message",
        "metadata",
    }

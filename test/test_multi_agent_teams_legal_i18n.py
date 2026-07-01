"""法律多智能体团队元数据国际化测试。"""

import pytest
from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.agents.multi_agent_collaboration import LegalContractReviewTeam
from src.shuyixiao_agent.auth import storage


AGENT_IDS = [
    "contract_reviewer",
    "clause_risk_analyzer",
    "legal_researcher",
    "drafting_specialist",
    "compliance_checker",
    "audit_recorder",
]
ZH_DISPLAY_NAMES = ["合同审查协调员", "条款风险分析师", "法律研究员", "法律文书起草专家", "合规审查专员", "审计留痕记录员"]
EN_DISPLAY_NAMES = ["Contract Review Coordinator", "Clause Risk Analyst", "Legal Researcher", "Legal Drafting Specialist", "Compliance Reviewer", "Audit Recorder"]
RU_DISPLAY_NAMES = ["Координатор проверки договоров", "Аналитик рисков договорных условий", "Юридический исследователь", "Специалист по юридическим документам", "Специалист по комплаенсу", "Специалист по аудиторскому следу"]


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    test_client = TestClient(web_app.app)
    response = test_client.post("/api/auth/login", json={"username": "admin", "password": "admin-secret"})
    assert response.status_code == 200
    return test_client


def _teams(client: TestClient, lang=None) -> dict:
    headers = {"X-User-Lang": lang} if lang else None
    response = client.get("/api/multi-agent/teams", headers=headers)
    assert response.status_code == 200
    return response.json()["teams"]


def _legal_agents(teams: dict) -> list[dict]:
    return teams["legal_contract_review"]["agents"]


def test_teams_default_lang_zh(client):
    legal_team = _teams(client)["legal_contract_review"]
    assert legal_team["name"] == "法律合同审查团队"
    assert [agent["display_name"] for agent in legal_team["agents"]] == ZH_DISPLAY_NAMES


def test_teams_xuserlang_en_legal_agents(client):
    legal_team = _teams(client, "en")["legal_contract_review"]
    assert legal_team["name"] == "Legal Contract Review Team"
    assert [agent["display_name"] for agent in legal_team["agents"]] == EN_DISPLAY_NAMES
    assert legal_team["use_cases"][-1] == "Legal research"


def test_teams_xuserlang_ru_legal_agents(client):
    legal_team = _teams(client, "ru")["legal_contract_review"]
    assert legal_team["name"] == "Команда юридической проверки договоров"
    assert [agent["display_name"] for agent in legal_team["agents"]] == RU_DISPLAY_NAMES


def test_teams_response_structure_unchanged(client):
    teams = _teams(client, "en")
    assert set(teams) == {"legal_contract_review"}
    agents = _legal_agents(teams)
    assert [agent["name"] for agent in agents] == AGENT_IDS
    assert all({"name", "display_name", "role", "description", "expertise"} <= set(agent) for agent in agents)
    assert teams["legal_contract_review"]["selection_policy"]["required_agent_names"] == ["contract_reviewer"]


def test_agent_profile_metadata_with_i18n_prefix():
    agent = LegalContractReviewTeam.get_agents()[0]
    metadata = web_app._agent_profile_metadata(agent, "en")
    assert agent.i18n_prefix == "agent.contract_reviewer"
    assert metadata["name"] == "contract_reviewer"
    assert metadata["display_name"] == "Contract Review Coordinator"
    assert metadata["description"] == "Coordinates the overall contract review"
    assert metadata["expertise"] == ["Contract review", "Task decomposition", "Risk consolidation", "Review conclusions"]

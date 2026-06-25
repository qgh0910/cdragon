"""法律合同审查团队领域路由策略测试。"""

from dataclasses import FrozenInstanceError

import pytest

from src.shuyixiao_agent.agents.multi_agent_collaboration import (
    LegalAgentSelectionError,
    LegalContractReviewTeam,
)


EXPECTED_TASK_DEFAULTS = {
    "contract_review": (
        "contract_reviewer",
        "clause_risk_analyzer",
        "legal_researcher",
        "compliance_checker",
    ),
    "risk_identification": (
        "contract_reviewer",
        "clause_risk_analyzer",
    ),
    "revision_suggestions": (
        "contract_reviewer",
        "clause_risk_analyzer",
        "legal_researcher",
        "drafting_specialist",
    ),
    "legal_research": (
        "contract_reviewer",
        "legal_researcher",
    ),
    "compliance_analysis": (
        "contract_reviewer",
        "compliance_checker",
        "legal_researcher",
    ),
    "review_summary": (
        "contract_reviewer",
        "clause_risk_analyzer",
    ),
    "legal_document_generation": (
        "contract_reviewer",
        "legal_researcher",
        "drafting_specialist",
    ),
    "redline_comparison": (
        "contract_reviewer",
        "clause_risk_analyzer",
        "compliance_checker",
    ),
    "approval_flow_suggestion": (
        "contract_reviewer",
        "clause_risk_analyzer",
        "compliance_checker",
    ),
}

EXPECTED_CAPABILITY_GAPS = {
    "clause_risk_analyzer": "可能缺少条款级风险识别与风险分级",
    "legal_researcher": "可能缺少可核验的法律依据与来源",
    "drafting_specialist": "可能缺少可直接使用的修改建议或替代条款",
    "compliance_checker": "可能缺少监管规则映射与合规红线检查",
    "audit_recorder": "可能缺少协作层审计摘要与引用完整性检查",
}


def test_selection_policy_matches_the_finalized_legal_team_contract():
    """领域策略应完整覆盖九种任务，且只引用已注册法律 Agent。"""
    policy = LegalContractReviewTeam.get_selection_policy()
    team_agent_names = {
        agent.name for agent in LegalContractReviewTeam.get_agents()
    }

    assert policy.default_task_type == "contract_review"
    assert policy.required_agent_names == ("contract_reviewer",)
    assert dict(policy.task_defaults) == EXPECTED_TASK_DEFAULTS
    assert dict(policy.capability_gaps) == EXPECTED_CAPABILITY_GAPS
    assert set(policy.required_agent_names) <= team_agent_names
    assert all(
        set(default_names) <= team_agent_names
        for default_names in policy.task_defaults.values()
    )
    assert set(policy.capability_gaps) <= team_agent_names


def test_selection_policy_is_immutable():
    """调用方不能在运行时修改领域策略。"""
    policy = LegalContractReviewTeam.get_selection_policy()

    with pytest.raises(FrozenInstanceError):
        policy.default_task_type = "legal_research"
    with pytest.raises(TypeError):
        policy.task_defaults["contract_review"] = ("contract_reviewer",)
    with pytest.raises(TypeError):
        policy.capability_gaps["audit_recorder"] = "changed"


@pytest.mark.parametrize(
    (
        "legal_task_type",
        "selected_agent_names",
        "expected_task_type",
        "expected_names",
        "expected_source",
        "expected_missing",
    ),
    [
        (
            None,
            None,
            "contract_review",
            (
                "contract_reviewer",
                "clause_risk_analyzer",
                "legal_researcher",
                "compliance_checker",
            ),
            "template_default",
            (),
        ),
        (
            "contract_review",
            list(EXPECTED_TASK_DEFAULTS["contract_review"]),
            "contract_review",
            (
                "contract_reviewer",
                "clause_risk_analyzer",
                "legal_researcher",
                "compliance_checker",
            ),
            "template_default",
            (),
        ),
        (
            "risk_identification",
            [],
            "risk_identification",
            ("contract_reviewer",),
            "user_override",
            ("clause_risk_analyzer",),
        ),
        (
            " legal_research ",
            [
                " legal_researcher ",
                "contract_reviewer",
                "legal_researcher",
            ],
            "legal_research",
            ("contract_reviewer", "legal_researcher"),
            "template_default",
            (),
        ),
        (
            "revision_suggestions",
            ["drafting_specialist", "contract_reviewer"],
            "revision_suggestions",
            ("contract_reviewer", "drafting_specialist"),
            "user_override",
            ("clause_risk_analyzer", "legal_researcher"),
        ),
        (
            "legal_research",
            ["audit_recorder", "legal_researcher"],
            "legal_research",
            (
                "contract_reviewer",
                "legal_researcher",
                "audit_recorder",
            ),
            "user_override",
            (),
        ),
    ],
)
def test_resolve_selection_normalizes_inputs_and_uses_stable_team_order(
    legal_task_type,
    selected_agent_names,
    expected_task_type,
    expected_names,
    expected_source,
    expected_missing,
):
    result = LegalContractReviewTeam.resolve_selection(
        legal_task_type,
        selected_agent_names,
    )

    assert result.legal_task_type == expected_task_type
    assert result.selected_agent_names == expected_names
    assert result.selection_source == expected_source
    assert result.missing_recommended_agent_names == expected_missing


def test_missing_recommended_agents_and_capability_gaps_use_the_same_order():
    result = LegalContractReviewTeam.resolve_selection(
        "revision_suggestions",
        ["contract_reviewer"],
    )

    expected_missing = (
        "clause_risk_analyzer",
        "legal_researcher",
        "drafting_specialist",
    )
    assert result.missing_recommended_agent_names == expected_missing
    assert tuple(gap.agent_name for gap in result.capability_gaps) == expected_missing
    assert tuple(gap.message for gap in result.capability_gaps) == tuple(
        EXPECTED_CAPABILITY_GAPS[name] for name in expected_missing
    )


@pytest.mark.parametrize("legal_task_type", ["", "   ", "unknown_task"])
def test_invalid_legal_task_type_has_a_stable_error_code(legal_task_type):
    with pytest.raises(LegalAgentSelectionError) as exc_info:
        LegalContractReviewTeam.resolve_selection(legal_task_type, None)

    assert exc_info.value.code == "invalid_legal_task_type"


@pytest.mark.parametrize(
    "selected_agent_names",
    [
        [""],
        ["   "],
        ["product_manager"],
        [123],
    ],
)
def test_invalid_legal_agent_name_has_a_stable_error_code(
    selected_agent_names,
):
    with pytest.raises(LegalAgentSelectionError) as exc_info:
        LegalContractReviewTeam.resolve_selection(
            "contract_review",
            selected_agent_names,
        )

    assert exc_info.value.code == "invalid_legal_agent_name"


def test_compliance_policy_order_does_not_override_stable_team_order():
    policy = LegalContractReviewTeam.get_selection_policy()
    assert policy.task_defaults["compliance_analysis"] == (
        "contract_reviewer",
        "compliance_checker",
        "legal_researcher",
    )

    result = LegalContractReviewTeam.resolve_selection(
        "compliance_analysis",
        list(policy.task_defaults["compliance_analysis"]),
    )

    assert result.selected_agent_names == (
        "contract_reviewer",
        "legal_researcher",
        "compliance_checker",
    )
    assert result.selection_source == "template_default"

"""多智能体 prompt 上下文瘦身测试。"""

import json

import pytest
from fastapi import HTTPException

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.agents.multi_agent_collaboration import (
    AgentProfile,
    AgentRole,
    LegalCollaborationExecutionPolicy,
    MultiAgentCollaboration,
)


class _FakeLLM:
    """避免测试触发真实 LLM。"""

    def simple_chat(self, prompt, timeout=None):
        return "ok"


def test_format_context_for_prompt_uses_summary_and_omits_full_contract_structure():
    collaboration = MultiAgentCollaboration(
        llm_client=_FakeLLM(), verbose=False, rag_agent=None
    )
    large_structure = {
        "clauses": [
            {"clause_id": "clause_0001", "content": "不得进入 prompt 的完整条款正文" * 200}
        ],
        "raw_page_index": [{"text": "不得进入 prompt 的 pageindex" * 200}],
    }
    context = {
        "contract_text": "合同全文" * 1000,
        "contract_structure": large_structure,
        "contract_structure_summary": {
            "contract_type": "采购合同",
            "parties": ["甲方：A公司", "乙方：B公司"],
            "clause_count": 1,
            "key_clause_summary": [
                {
                    "clause_id": "clause_0001",
                    "title": "付款",
                    "summary": "付款安排",
                }
            ],
        },
        "uploaded_file_path": "/private/path/contract.txt",
        "uploaded_file_id": "20260616_120000_abcdef123456",
    }

    formatted = collaboration._format_context_for_prompt(context)

    assert "采购合同" in formatted
    assert "甲方：A公司" in formatted
    assert "clause_0001" in formatted
    assert "不得进入 prompt 的完整条款正文" not in formatted
    assert "raw_page_index" not in formatted
    assert "/private/path/contract.txt" not in formatted
    assert formatted.count("合同全文") <= 5


def test_get_agent_response_uses_formatted_context_instead_of_raw_dict_dump():
    captured = {}

    class _RecordingLLM:
        def simple_chat(self, prompt, timeout=None):
            captured["prompt"] = prompt
            return "ok"

    collaboration = MultiAgentCollaboration(
        llm_client=_RecordingLLM(), verbose=False, rag_agent=None
    )
    collaboration.register_agent(
        AgentProfile(
            name="contract_reviewer",
            role=AgentRole.COORDINATOR,
            description="合同审查",
            expertise=["合同审查"],
            system_prompt="你是合同审查员",
        )
    )

    collaboration.get_agent_response(
        "contract_reviewer",
        "审查合同",
        context={
            "contract_structure": {"secret": "完整结构不应出现"},
            "contract_structure_summary": {"contract_type": "采购合同"},
        },
    )

    assert "采购合同" in captured["prompt"]
    assert "完整结构不应出现" not in captured["prompt"]
    assert "- contract_structure:" not in captured["prompt"]


def test_build_legal_base_context_truncates_summarizes_and_filters_contract_payload():
    """法律基础 context 只保留安全摘要字段，并丢弃路径、pageindex 和客户端阶段键。"""
    source_refs = [
        {
            "file_id": f"file-{index}",
            "source_name": "../contract.txt",
            "document_type": "txt",
            "page_number": index,
            "paragraph_index": index + 1,
            "text_preview": "不应保留",
            "file_path": "/private/secret.txt",
            "unknown": "drop",
        }
        for index in range(5)
    ]
    context = {
        "contract_text": "合同正文" * 1000,
        "uploaded_file_name": "C:\\private\\contract.txt",
        "uploaded_file_id": "file-legal-review-001",
        "legal_task_type": "client_forged",
        "review_focus": "重点关注付款与违约责任",
        "contract_type": "采购合同",
        "party_a": "甲方",
        "party_b": "乙方",
        "contract_structure": {"secret": "完整结构"},
        "raw_page_index": [{"text": "原始页索引"}],
        "page_index": [{"text": "原始页索引"}],
        "uploaded_file_path": "/private/secret.txt",
        "coordinator_analysis": "客户端伪造成果",
        "advisor_results": {"legal_researcher": "客户端伪造成果"},
        "unknown_complex": {"nested": ["drop"]},
        "contract_structure_summary": {
            "contract_type": "采购合同",
            "parties": ["甲方", "乙方"] + ["多余主体"] * 20,
            "amount": [f"{index}万元" for index in range(12)],
            "term": [f"第{index}期" for index in range(12)],
            "effective_date": [f"2026-06-{index:02d}" for index in range(1, 13)],
            "clause_count": 30,
            "warning_count": 25,
            "unknown": "drop",
            "key_clause_summary": [
                {
                    "clause_id": f"c{index}",
                    "title": "付款",
                    "clause_type": "payment",
                    "summary": "付款摘要" * (200 if index == 0 else 1),
                    "source_refs": source_refs,
                    "content": "不应保留的完整条款",
                }
                for index in range(25)
            ],
            "warnings": [f"风险提示{index}" for index in range(25)],
        },
    }

    normalized = web_app._build_legal_base_context(context, "contract_review")

    assert normalized["legal_task_type"] == "contract_review"
    assert normalized["uploaded_file_name"] == "contract.txt"
    assert len(normalized["contract_text"]) <= 1200
    assert normalized["contract_text"].endswith("…[内容已截断]")

    summary = normalized["contract_structure_summary"]
    assert summary["contract_type"] == "采购合同"
    assert len(summary["parties"]) == 10
    assert len(summary["amount"]) == 10
    assert len(summary["term"]) == 10
    assert len(summary["effective_date"]) == 10
    assert len(summary["key_clause_summary"]) == 20
    assert len(summary["warnings"]) == 20
    assert "unknown" not in summary

    first_clause = summary["key_clause_summary"][0]
    assert set(first_clause) == {
        "clause_id",
        "title",
        "clause_type",
        "summary",
        "source_refs",
    }
    assert len(first_clause["summary"]) <= 500
    assert len(first_clause["source_refs"]) == 3
    assert first_clause["source_refs"][0] == {
        "file_id": "file-0",
        "source_name": "contract.txt",
        "document_type": "txt",
        "page_number": 0,
        "paragraph_index": 1,
    }

    serialized = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    assert len(serialized) <= 6000
    for forbidden_text in [
        "完整结构",
        "原始页索引",
        "private/secret",
        "text_preview",
        "不应保留",
        "客户端伪造成果",
        "unknown_complex",
    ]:
        assert forbidden_text not in serialized


@pytest.mark.parametrize(
    ("raw_name", "expected_name"),
    [
        ("C:\\private\\nested\\contract.txt", "contract.txt"),
        ("/private/nested/contract.docx", "contract.docx"),
    ],
)
def test_build_legal_base_context_keeps_only_uploaded_file_basename(
    raw_name,
    expected_name,
):
    """Windows 和 POSIX 路径都只能暴露 basename。"""
    normalized = web_app._build_legal_base_context(
        {"uploaded_file_name": raw_name},
        "contract_review",
    )

    assert normalized["uploaded_file_name"] == expected_name


@pytest.mark.parametrize(
    "context",
    [
        {"contract_text": ["not", "a", "string"]},
        {"uploaded_file_name": {"name": "contract.txt"}},
        {"contract_structure_summary": "not-a-dict"},
    ],
)
def test_build_legal_base_context_rejects_wrong_field_types(context):
    """法律 context 字段类型错误应返回 422，而不是进入 prompt 或运行时。"""
    with pytest.raises(HTTPException) as exc_info:
        web_app._build_legal_base_context(context, "contract_review")

    assert exc_info.value.status_code == 422


def test_legal_policy_prompt_context_has_untrusted_boundary_and_total_budget():
    """法律策略下 prompt context 必须有不可信边界，并限制动态 context 总量。"""
    collaboration = MultiAgentCollaboration(
        llm_client=_FakeLLM(),
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    context = {
        "contract_text": "合同正文" * 3000,
        "legal_task_type": "compliance_analysis",
        "uploaded_file_name": "contract.txt",
        "coordinator_analysis": "主控分析" * 800,
        "advisor_results": {"legal_researcher": "检索依据" * 800},
        "failed_agent_names": ["compliance_checker"],
    }

    formatted = collaboration._format_context_for_prompt(context)

    assert "BEGIN_UNTRUSTED_CONTEXT" in formatted
    assert "END_UNTRUSTED_CONTEXT" in formatted
    dynamic_part = formatted.split("BEGIN_UNTRUSTED_CONTEXT", 1)[1].split(
        "END_UNTRUSTED_CONTEXT",
        1,
    )[0]
    assert (
        len(dynamic_part)
        <= collaboration.execution_policy.context_limits.agent_context_max_chars
    )
    assert "contract_text_summary" in dynamic_part
    assert "legal_task_type" in dynamic_part
    assert "coordinator_analysis" in dynamic_part
    assert "failed_agent_names" in dynamic_part


def test_legal_policy_prompt_context_filters_sensitive_keys_but_allows_stage_keys():
    """法律策略只允许服务端生成的阶段键，不透传 all_work、路径或未知复杂字段。"""
    collaboration = MultiAgentCollaboration(
        llm_client=_FakeLLM(),
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    context = {
        "contract_text": "采购合同正文",
        "contract_structure": {"secret": "完整结构不得进入 prompt"},
        "raw_page_index": [{"text": "pageindex 不得进入 prompt"}],
        "uploaded_file_path": "/private/secret/contract.txt",
        "all_work": {"contract_reviewer": "不允许的完整工作集"},
        "unknown_complex": {"secret": "未知复杂字段"},
        "coordinator_analysis": "主控分析摘要",
        "advisor_results": {"legal_researcher": "检索摘要"},
        "specialist_results": {"clause_risk_analyzer": "风险摘要"},
        "executor_results": {"drafting_specialist": "起草摘要"},
        "prior_work_results": {"compliance_checker": "合规摘要"},
        "failed_agent_names": ["audit_recorder"],
    }

    formatted = collaboration._format_context_for_prompt(context)

    assert "coordinator_analysis" in formatted
    assert "advisor_results" in formatted
    assert "specialist_results" in formatted
    assert "executor_results" in formatted
    assert "prior_work_results" in formatted
    assert "failed_agent_names" in formatted
    for forbidden in [
        "完整结构不得进入 prompt",
        "pageindex 不得进入 prompt",
        "/private/secret/contract.txt",
        "all_work",
        "不允许的完整工作集",
        "unknown_complex",
        "未知复杂字段",
    ]:
        assert forbidden not in formatted


def test_legacy_policy_none_keeps_exact_context_prompt_format():
    """未启用法律策略时，context prompt 格式保持既有精确输出。"""
    collaboration = MultiAgentCollaboration(
        llm_client=_FakeLLM(),
        verbose=False,
        execution_policy=None,
    )
    context = {
        "contract_text": "合同\n正文",
        "contract_structure_summary": {"contract_type": "采购合同"},
        "uploaded_file_id": "file-1",
        "clause_refs": ["条款1", "条款2"],
        "round": 2,
        "all_work": {"secret": "legacy 也不允许"},
    }

    formatted = collaboration._format_context_for_prompt(context)

    assert formatted == (
        "- contract_text_summary: 合同 正文\n"
        '- contract_structure_summary: {"contract_type":"采购合同"}\n'
        "- uploaded_file_id: file-1\n"
        '- clause_refs: ["条款1","条款2"]\n'
        "- round: 2"
    )

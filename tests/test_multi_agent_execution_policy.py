"""法律多智能体执行策略隔离测试。"""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

from src.shuyixiao_agent.agents import multi_agent_collaboration as collaboration_module
from src.shuyixiao_agent.agents.multi_agent_collaboration import (
    AgentProfile,
    AgentRole,
    CollaborationMode,
    LegalCollaborationExecutionPolicy,
    MultiAgentCollaboration,
)


class _FakeLLM:
    """仅用于构造协作对象，不触发真实 LLM 调用。"""

    def invoke(self, messages):
        raise AssertionError("本测试不应触发 LLM 调用")


class _PromptRecordingLLM:
    """按 Agent 标记返回脚本结果，并记录每次 prompt。"""

    def __init__(self, scripts, synthesis_output="整合完成"):
        self.scripts = {
            agent_name: list(outcomes)
            for agent_name, outcomes in scripts.items()
        }
        self.synthesis_output = synthesis_output
        self.prompts = []

    def simple_chat(self, prompt, timeout=None):
        self.prompts.append(prompt)
        if "AGENT_MARKER:" not in prompt:
            return self.synthesis_output

        agent_name = prompt.split("AGENT_MARKER:", 1)[1].splitlines()[0].strip()
        outcomes = self.scripts.get(agent_name, [f"{agent_name} 完成"])
        if len(outcomes) > 1:
            outcome = outcomes.pop(0)
        else:
            outcome = outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_execution_policy_defaults_to_legacy_none():
    """默认构造必须保持旧行为，不自动启用法律执行策略。"""
    collaboration = MultiAgentCollaboration(_FakeLLM(), verbose=False)

    assert collaboration.execution_policy is None


def test_legal_execution_policy_uses_finalized_limits():
    """法律执行策略应使用最终方案固定预算。"""
    policy = collaboration_module.LegalCollaborationExecutionPolicy()

    assert policy.safe_context_inheritance is True
    assert policy.structured_agent_results is True
    assert policy.bounded_synthesis is True
    assert policy.context_limits.contract_text_max_chars == 1200
    assert policy.context_limits.context_value_max_chars == 4000
    assert policy.context_limits.stage_excerpt_max_chars == 3000
    assert policy.context_limits.agent_context_max_chars == 12000
    assert policy.context_limits.synthesis_item_max_chars == 3000
    assert policy.context_limits.synthesis_dynamic_max_chars == 20000
    assert policy.context_limits.clause_refs_max_items == 20


class _RecordingCollaboration(MultiAgentCollaboration):
    """记录层级协作传给每个 Agent 的 context。"""

    def __init__(self, *args, failed_agents=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_agents = set(failed_agents or [])
        self.calls = []

    def _invoke_agent(self, agent_name, input_text, context=None):
        self.calls.append(
            {
                "agent": agent_name,
                "input_text": input_text,
                "context": copy.deepcopy(context or {}),
            }
        )
        if agent_name in self.failed_agents:
            return collaboration_module.AgentCallResult(
                status="failed",
                response="",
                safe_error_code="agent_execution_failed",
                safe_error_message="智能体执行失败，已跳过该专业结果，请人工复核。",
            )
        return collaboration_module.AgentCallResult(
            status="completed",
            response=f"{agent_name} 已完成",
        )

    def _synthesize_results(self, agent_contributions, original_task):
        return "已整合"


def _profile(name, role):
    return AgentProfile(
        name=name,
        role=role,
        description=name,
        expertise=[name],
        system_prompt=f"{name} system prompt",
    )


def _marked_profile(name, role):
    return AgentProfile(
        name=name,
        role=role,
        description=name,
        expertise=[name],
        system_prompt=f"AGENT_MARKER: {name}\n请完成任务。",
        enable_rag=False,
    )


def _register_legal_hierarchy(collaboration):
    collaboration.register_agents(
        [
            _profile("contract_reviewer", AgentRole.COORDINATOR),
            _profile("legal_researcher", AgentRole.ADVISOR),
            _profile("clause_risk_analyzer", AgentRole.SPECIALIST),
            _profile("drafting_specialist", AgentRole.EXECUTOR),
            _profile("compliance_checker", AgentRole.REVIEWER),
            _profile("audit_recorder", AgentRole.REVIEWER),
        ]
    )


def _legal_context():
    return {
        "contract_text": "合同摘要",
        "contract_structure_summary": {"contract_type": "采购合同"},
        "legal_task_type": "contract_review",
        "uploaded_file_name": "contract.txt",
    }


def _call_contexts(collaboration):
    return {call["agent"]: call["context"] for call in collaboration.calls}


def test_legal_hierarchical_context_preserves_base_context_for_every_stage():
    """法律层级模式下每个阶段都必须继承规范化 base context。"""
    collaboration = _RecordingCollaboration(
        _FakeLLM(),
        mode=CollaborationMode.HIERARCHICAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    _register_legal_hierarchy(collaboration)

    collaboration.collaborate("审查合同", context=_legal_context())

    for call in collaboration.calls:
        context = call["context"]
        assert context.get("contract_structure_summary") == {"contract_type": "采购合同"}
        assert context.get("legal_task_type") == "contract_review"
        assert context.get("uploaded_file_name") == "contract.txt"


def test_legal_hierarchical_context_adds_direct_stage_dependencies():
    """法律层级模式应按阶段追加 coordinator/advisor/specialist/executor 成果。"""
    collaboration = _RecordingCollaboration(
        _FakeLLM(),
        mode=CollaborationMode.HIERARCHICAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    _register_legal_hierarchy(collaboration)

    collaboration.collaborate("审查合同", context=_legal_context())
    contexts = _call_contexts(collaboration)

    assert "coordinator_analysis" in contexts["legal_researcher"]
    assert "coordinator_analysis" in contexts["clause_risk_analyzer"]
    assert "advisor_results" in contexts["clause_risk_analyzer"]
    assert "coordinator_analysis" in contexts["drafting_specialist"]
    assert "advisor_results" in contexts["drafting_specialist"]
    assert "specialist_results" in contexts["drafting_specialist"]
    assert "prior_work_results" in contexts["compliance_checker"]
    assert "prior_work_results" in contexts["audit_recorder"]


def test_legal_hierarchical_reviewer_context_is_rebuilt_for_each_reviewer():
    """多个 reviewer 的 prior_work_results 必须按当时已完成成果动态生成。"""
    collaboration = _RecordingCollaboration(
        _FakeLLM(),
        mode=CollaborationMode.HIERARCHICAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    _register_legal_hierarchy(collaboration)

    collaboration.collaborate("审查合同", context=_legal_context())
    contexts = _call_contexts(collaboration)

    assert "prior_work_results" in contexts["compliance_checker"]
    assert "prior_work_results" in contexts["audit_recorder"]
    compliance_prior = contexts["compliance_checker"]["prior_work_results"]
    audit_prior = contexts["audit_recorder"]["prior_work_results"]
    assert "audit_recorder" not in compliance_prior
    assert "compliance_checker" in audit_prior
    assert "compliance_checker 已完成" in audit_prior


def test_legal_hierarchical_failed_advisor_only_flows_as_failed_agent_name():
    """失败的上游 Agent 不得生成 advisor_results，只能作为失败角色名向下游提示。"""
    collaboration = _RecordingCollaboration(
        _FakeLLM(),
        mode=CollaborationMode.HIERARCHICAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
        failed_agents={"legal_researcher"},
    )
    _register_legal_hierarchy(collaboration)

    collaboration.collaborate("审查合同", context=_legal_context())
    contexts = _call_contexts(collaboration)

    for agent_name in [
        "clause_risk_analyzer",
        "drafting_specialist",
        "compliance_checker",
        "audit_recorder",
    ]:
        context = contexts[agent_name]
        assert context.get("failed_agent_names") == ["legal_researcher"]
        assert "advisor_results" not in context
        assert "智能体执行失败" not in str(context)


def test_legacy_hierarchical_policy_none_keeps_old_context_shape():
    """未启用法律策略时，层级模式保持旧的 analysis/plan/advice/all_work 组装。"""
    collaboration = _RecordingCollaboration(
        _FakeLLM(),
        mode=CollaborationMode.HIERARCHICAL,
        verbose=False,
        execution_policy=None,
    )
    _register_legal_hierarchy(collaboration)

    collaboration.collaborate("审查合同", context=_legal_context())
    contexts = _call_contexts(collaboration)

    assert contexts["legal_researcher"] == {"analysis": "contract_reviewer 已完成"}
    assert contexts["clause_risk_analyzer"] == {
        "plan": "contract_reviewer 已完成",
        "advice": ["legal_researcher 已完成"],
    }
    assert contexts["drafting_specialist"] == {
        "specialist_work": ["clause_risk_analyzer 已完成"]
    }
    assert "all_work" in contexts["compliance_checker"]
    assert "prior_work_results" not in contexts["compliance_checker"]


def _run_isolated_parallel_case(label, contract_type, failed_agent_name):
    """在线程内运行一个独立法律协作对象，返回结果和 LLM 记录。"""
    ok_agent = f"{label}_ok_agent"
    llm = _PromptRecordingLLM(
        {
            ok_agent: [f"{label} 成功结果"],
            failed_agent_name: [
                RuntimeError(f"{label} failure /private/{label}/secret.txt")
            ],
        },
        synthesis_output=f"{label} 整合结果",
    )
    collaboration = MultiAgentCollaboration(
        llm,
        mode=CollaborationMode.PARALLEL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    collaboration.register_agents(
        [
            _marked_profile(ok_agent, AgentRole.COORDINATOR),
            _marked_profile(failed_agent_name, AgentRole.REVIEWER),
        ]
    )

    result = collaboration.collaborate(
        f"审查 {label}",
        context={
            "contract_type": contract_type,
            "legal_task_type": "contract_review",
        },
    )
    return {
        "label": label,
        "result": result,
        "prompts": list(llm.prompts),
        "messages": [message.__dict__ for message in result.messages],
        "tasks": [task.__dict__ for task in result.tasks],
    }


def test_parallel_collaborations_do_not_share_context_failures_or_prompts():
    """两个独立协作对象并发运行时，贡献、消息、任务和 prompt 不得串扰。"""
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(
            _run_isolated_parallel_case,
            "case_a",
            "采购合同A",
            "case_a_failed_agent",
        )
        future_b = executor.submit(
            _run_isolated_parallel_case,
            "case_b",
            "租赁合同B",
            "case_b_failed_agent",
        )
        case_a = future_a.result()
        case_b = future_b.result()

    assert set(case_a["result"].agent_contributions) == {
        "case_a_ok_agent",
        "case_a_failed_agent",
    }
    assert set(case_b["result"].agent_contributions) == {
        "case_b_ok_agent",
        "case_b_failed_agent",
    }
    assert (
        case_a["result"].agent_contributions["case_a_failed_agent"]["status"]
        == "failed"
    )
    assert (
        case_b["result"].agent_contributions["case_b_failed_agent"]["status"]
        == "failed"
    )

    serialized_a = json.dumps(
        {
            "contributions": case_a["result"].agent_contributions,
            "messages": case_a["messages"],
            "tasks": case_a["tasks"],
            "prompts": case_a["prompts"],
        },
        ensure_ascii=False,
    )
    serialized_b = json.dumps(
        {
            "contributions": case_b["result"].agent_contributions,
            "messages": case_b["messages"],
            "tasks": case_b["tasks"],
            "prompts": case_b["prompts"],
        },
        ensure_ascii=False,
    )
    assert "case_b" not in serialized_a
    assert "租赁合同B" not in serialized_a
    assert "case_a" not in serialized_b
    assert "采购合同A" not in serialized_b
    assert "采购合同A" in serialized_a
    assert "租赁合同B" in serialized_b


def test_same_collaboration_sequential_call_clears_messages_between_runs():
    """同一协作对象连续调用时，第二次结果不应带入第一次 messages/tasks。"""
    llm = _PromptRecordingLLM(
        {"contract_reviewer": ["第一次响应", "第二次响应"]},
        synthesis_output="整合完成",
    )
    collaboration = MultiAgentCollaboration(
        llm,
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    collaboration.register_agent(
        _marked_profile("contract_reviewer", AgentRole.COORDINATOR)
    )

    first = collaboration.collaborate(
        "第一次任务",
        context={"contract_type": "采购合同", "legal_task_type": "contract_review"},
    )
    prompt_count_after_first = len(llm.prompts)
    second = collaboration.collaborate(
        "第二次任务",
        context={"contract_type": "租赁合同", "legal_task_type": "legal_research"},
    )

    assert "第一次任务" in json.dumps(
        [message.__dict__ for message in first.messages],
        ensure_ascii=False,
    )
    second_messages = json.dumps(
        [message.__dict__ for message in second.messages],
        ensure_ascii=False,
    )
    second_prompts = "\n".join(llm.prompts[prompt_count_after_first:])
    assert "第二次任务" in second_messages
    assert "第二次任务" in second_prompts
    assert "第一次任务" not in second_messages
    assert "第一次任务" not in second_prompts
    assert second.tasks == []


def test_same_collaboration_peer_to_peer_resets_failure_attempt_counts():
    """对等模式连续调用时，第二次不能继承第一次失败尝试计数。"""
    llm = _PromptRecordingLLM(
        {
            "contract_reviewer": [
                RuntimeError("first round failed /private/first.txt"),
                RuntimeError("second round failed /private/first.txt"),
                "second call first success",
                "second call second success",
            ]
        },
        synthesis_output="整合完成",
    )
    collaboration = MultiAgentCollaboration(
        llm,
        mode=CollaborationMode.PEER_TO_PEER,
        verbose=False,
        max_rounds=2,
        execution_policy=LegalCollaborationExecutionPolicy(),
    )
    collaboration.register_agent(
        _marked_profile("contract_reviewer", AgentRole.COORDINATOR)
    )

    first = collaboration.collaborate(
        "第一次对等任务",
        context={"legal_task_type": "contract_review"},
    )
    second = collaboration.collaborate(
        "第二次对等任务",
        context={"legal_task_type": "contract_review"},
    )

    first_contribution = first.agent_contributions["contract_reviewer"]
    second_contribution = second.agent_contributions["contract_reviewer"]
    assert first_contribution["status"] == "failed"
    assert first_contribution["attempt_count"] == 2
    assert first_contribution["failed_attempt_count"] == 2
    assert second_contribution["status"] == "completed"
    assert second_contribution["attempt_count"] == 2
    assert second_contribution["failed_attempt_count"] == 0

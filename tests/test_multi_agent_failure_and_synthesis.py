"""法律多智能体结构化失败与 legacy 兼容红灯测试。"""

import json

import pytest

from src.shuyixiao_agent.agents.multi_agent_collaboration import (
    AgentProfile,
    AgentRole,
    LegalCollaborationExecutionPolicy,
    MultiAgentCollaboration,
)


class _ScriptedLLM:
    """根据 Agent system prompt 标记返回成功响应或抛出异常。"""

    def __init__(self, scripts, synthesis_outcomes=None):
        self.scripts = {
            agent_name: list(outcomes)
            for agent_name, outcomes in scripts.items()
        }
        self.synthesis_outcomes = list(
            synthesis_outcomes or ["整合后的法律审查结论"]
        )
        self.calls = []

    def simple_chat(self, prompt, timeout=None):
        if (
            "各 Agent 的贡献" in prompt
            or "BEGIN_UNTRUSTED_AGENT_RESULTS" in prompt
            or "AGENT_MARKER:" not in prompt
        ):
            self.calls.append(("synthesis", prompt))
            if len(self.synthesis_outcomes) > 1:
                outcome = self.synthesis_outcomes.pop(0)
            else:
                outcome = self.synthesis_outcomes[0]
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        agent_name = self._agent_name_from_prompt(prompt)
        self.calls.append((agent_name, prompt))
        outcomes = self.scripts.get(agent_name, [f"{agent_name} 默认成功"])
        if len(outcomes) > 1:
            outcome = outcomes.pop(0)
        else:
            outcome = outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    @staticmethod
    def _agent_name_from_prompt(prompt):
        marker = "AGENT_MARKER:"
        if marker not in prompt:
            return "unknown"
        return prompt.split(marker, 1)[1].splitlines()[0].strip()


def _agent(name, role):
    """构造带可识别 system prompt 的测试 Agent。"""
    return AgentProfile(
        name=name,
        role=role,
        description=f"{name} description",
        expertise=[name],
        system_prompt=f"AGENT_MARKER: {name}\n请完成你的任务。",
        priority=10 if role == AgentRole.COORDINATOR else 5,
    )


def _collaboration(
    mode,
    scripts,
    *,
    legal_policy=True,
    max_rounds=3,
    synthesis_outcomes=None,
):
    collaboration = MultiAgentCollaboration(
        _ScriptedLLM(scripts, synthesis_outcomes=synthesis_outcomes),
        mode=mode,
        verbose=False,
        max_rounds=max_rounds,
        execution_policy=(
            LegalCollaborationExecutionPolicy() if legal_policy else None
        ),
    )
    return collaboration


def _long_response(label):
    """构造能暴露未截断尾部的超长 Agent 输出。"""
    return f"{label}:" + ("有效审查意见" * 2400) + "TAIL_SHOULD_NOT_APPEAR"


@pytest.mark.parametrize(
    "mode",
    ["sequential", "parallel", "hierarchical", "peer_to_peer", "hybrid"],
)
def test_legal_policy_marks_partial_agent_failure_without_failing_whole_run(mode):
    """法律策略下，部分失败应结构化为 failed，成功 Agent 保持 completed。"""
    collaboration = _collaboration(
        mode,
        {
            "ok_agent": ["ok response"],
            "failed_agent": [
                RuntimeError("boom at /private/secret/contract.txt")
            ],
        },
    )
    collaboration.register_agents(
        [
            _agent("ok_agent", AgentRole.COORDINATOR),
            _agent("failed_agent", AgentRole.SPECIALIST),
        ]
    )

    result = collaboration.collaborate("请审查合同")

    assert result.success is True
    assert result.agent_contributions["ok_agent"]["status"] == "completed"
    assert result.agent_contributions["failed_agent"]["status"] == "failed"
    assert result.agent_contributions["failed_agent"]["error_code"] == (
        "agent_execution_failed"
    )
    assert "private/secret" not in json.dumps(
        result.agent_contributions,
        ensure_ascii=False,
    )


def test_legal_policy_all_failed_agents_returns_safe_failed_result():
    """法律策略下，全部失败应返回空 final_output 和安全错误。"""
    collaboration = _collaboration(
        "parallel",
        {
            "first_failed_agent": [
                RuntimeError("first leaked /private/secret/a.txt")
            ],
            "second_failed_agent": [
                RuntimeError("second leaked /private/secret/b.txt")
            ],
        },
    )
    collaboration.register_agents(
        [
            _agent("first_failed_agent", AgentRole.COORDINATOR),
            _agent("second_failed_agent", AgentRole.SPECIALIST),
        ]
    )

    result = collaboration.collaborate("请审查合同")

    assert result.success is False
    assert result.final_output == ""
    assert "private/secret" not in result.error_message
    assert "private/secret" not in json.dumps(
        result.agent_contributions,
        ensure_ascii=False,
    )


def test_legal_peer_to_peer_recovers_after_failed_attempt():
    """对等协作中失败后恢复，应记录尝试次数并保留最后成功响应。"""
    collaboration = _collaboration(
        "peer_to_peer",
        {
            "recovering_agent": [
                RuntimeError("round 1 failed /private/secret/retry.txt"),
                "round 2 success",
                "round 3 success",
            ],
        },
        max_rounds=3,
    )
    collaboration.register_agents(
        [_agent("recovering_agent", AgentRole.COORDINATOR)]
    )

    result = collaboration.collaborate("请审查合同")
    contribution = result.agent_contributions["recovering_agent"]

    assert contribution["status"] == "completed"
    assert contribution["attempt_count"] == 3
    assert contribution["failed_attempt_count"] == 1
    assert contribution["response"] == "round 3 success"
    assert "private/secret" not in json.dumps(contribution, ensure_ascii=False)


def test_legacy_policy_none_keeps_old_error_string_contract():
    """未启用法律策略时，同样异常仍保持旧字符串返回契约。"""
    collaboration = _collaboration(
        "parallel",
        {
            "legacy_failed_agent": [
                RuntimeError("legacy failure /private/secret/raw.txt")
            ],
        },
        legal_policy=False,
    )
    collaboration.register_agents(
        [_agent("legacy_failed_agent", AgentRole.COORDINATOR)]
    )

    result = collaboration.collaborate("实现普通任务")
    contribution = result.agent_contributions["legacy_failed_agent"]

    assert "status" not in contribution
    assert contribution["response"].startswith(
        "Agent legacy_failed_agent 执行失败:"
    )
    assert "/private/secret/raw.txt" in contribution["response"]


def test_legal_synthesis_prompt_uses_completed_only_boundary_and_budget():
    """法律最终整合 prompt 只能消费受限 completed 成果。"""
    collaboration = _collaboration(
        "parallel",
        {
            "completed_agent": [_long_response("completed_agent")],
            "failed_agent": [
                RuntimeError(
                    "failed raw /private/secret/failed.txt api-key sk-live-secret"
                )
            ],
        },
    )
    collaboration.register_agents(
        [
            _agent("completed_agent", AgentRole.COORDINATOR),
            _agent("failed_agent", AgentRole.SPECIALIST),
        ]
    )

    result = collaboration.collaborate("请审查合同")
    synthesis_prompt = next(
        prompt
        for call_type, prompt in collaboration.llm_client.calls
        if call_type == "synthesis"
    )

    assert result.success is True
    assert "BEGIN_UNTRUSTED_AGENT_RESULTS" in synthesis_prompt
    assert "END_UNTRUSTED_AGENT_RESULTS" in synthesis_prompt
    dynamic_part = synthesis_prompt.split(
        "BEGIN_UNTRUSTED_AGENT_RESULTS",
        1,
    )[1].split("END_UNTRUSTED_AGENT_RESULTS", 1)[0]
    assert len(dynamic_part) <= 20000
    assert "completed_agent" in dynamic_part
    assert "TAIL_SHOULD_NOT_APPEAR" not in dynamic_part
    assert "/private/secret/failed.txt" not in synthesis_prompt
    assert "sk-live-secret" not in synthesis_prompt


def test_legal_synthesis_success_records_execution_metadata():
    """法律最终整合成功时应写入权威 execution metadata。"""
    collaboration = _collaboration(
        "parallel",
        {
            "completed_agent": ["已完成审查"],
            "failed_agent": [RuntimeError("failed /private/secret/raw.txt")],
        },
    )
    collaboration.register_agents(
        [
            _agent("completed_agent", AgentRole.COORDINATOR),
            _agent("failed_agent", AgentRole.SPECIALIST),
        ]
    )

    result = collaboration.collaborate("请审查合同")

    assert result.metadata["execution"]["synthesis_status"] == "completed"
    assert result.metadata["execution"]["completed_agent_count"] == 1
    assert result.metadata["execution"]["failed_agent_count"] == 1


def test_legal_synthesis_failure_degrades_with_bounded_safe_markdown():
    """只有最终整合失败时，应返回受限确定性 Markdown 而非原始拼接。"""
    collaboration = _collaboration(
        "parallel",
        {"completed_agent": [_long_response("completed_agent")]},
        synthesis_outcomes=[
            RuntimeError(
                "synthesis exploded /private/secret/synthesis.txt api-key sk-live"
            )
        ],
    )
    collaboration.register_agents(
        [_agent("completed_agent", AgentRole.COORDINATOR)]
    )

    result = collaboration.collaborate("请审查合同")

    assert result.success is True
    assert result.final_output.startswith("# 法律多智能体协作降级报告")
    assert "最终整合已降级" in result.final_output
    assert result.metadata["execution"]["synthesis_status"] == "degraded"
    assert "/private/secret/synthesis.txt" not in result.final_output
    assert "sk-live" not in result.final_output
    assert "TAIL_SHOULD_NOT_APPEAR" not in result.final_output
    assert len(result.final_output) <= 24000


def test_legacy_synthesis_failure_keeps_old_fallback_and_empty_metadata():
    """未启用法律策略时，最终整合失败仍保持旧 fallback 契约。"""
    collaboration = _collaboration(
        "parallel",
        {"legacy_agent": ["legacy completed response"]},
        legal_policy=False,
        synthesis_outcomes=[
            RuntimeError("legacy synthesis failed /private/secret/raw.txt")
        ],
    )
    collaboration.register_agents(
        [_agent("legacy_agent", AgentRole.COORDINATOR)]
    )

    result = collaboration.collaborate("实现普通任务")

    assert result.success is True
    assert result.final_output.startswith("# 协作结果")
    assert "legacy completed response" in result.final_output
    assert result.metadata == {}

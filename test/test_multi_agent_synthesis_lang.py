"""多智能体最终综合 prompt 的输出语言测试。"""

from shuyixiao_agent.agents import multi_agent_collaboration as collaboration_module
from shuyixiao_agent.agents.multi_agent_collaboration import (
    AgentProfile,
    AgentRole,
    CollaborationMode,
    LegalCollaborationExecutionPolicy,
    MultiAgentCollaboration,
    SynthesisResult,
)
from shuyixiao_agent.i18n.llm_instructions import build_llm_language_suffix
from shuyixiao_agent.i18n.translator import translate


class _RecordingLLM:
    def __init__(self, response: str = "ok"):
        self.response = response
        self.prompts: list[str] = []

    def simple_chat(self, prompt, timeout=None):
        self.prompts.append(prompt)
        return self.response


class _FailingLLM:
    def simple_chat(self, prompt, timeout=None):
        raise RuntimeError("simulated timeout")


class _SequenceLLM:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.prompts = []

    def simple_chat(self, prompt, timeout=None):
        self.prompts.append(prompt)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _reviewer(name: str = "reviewer") -> AgentProfile:
    return AgentProfile(
        name=name,
        role=AgentRole.SPECIALIST,
        description="审查合同条款",
        expertise=["合同审查"],
        system_prompt="你是一名合同审查专家。",
    )


def _mock_contributions():
    return {
        "reviewer": {
            "response": "合同存在付款条款风险",
            "status": "completed",
        },
    }


def _record_synthesis_prompt(lang: str) -> str:
    response = "Готово." if lang == "ru" else "ok"
    llm = _RecordingLLM(response=response)
    collaboration = MultiAgentCollaboration(
        llm_client=llm,
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        lang=lang,
    )
    collaboration.register_agent(_reviewer())

    collaboration._synthesize_results(_mock_contributions(), "原始任务描述")

    assert len(llm.prompts) == 1
    return llm.prompts[0]


def _record_legal_synthesis_prompt(lang: str) -> str:
    response = "Готово." if lang == "ru" else "ok"
    llm = _RecordingLLM(response=response)
    collaboration = MultiAgentCollaboration(
        llm_client=llm,
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(
            bounded_synthesis=True,
        ),
        lang=lang,
    )
    collaboration.register_agent(_reviewer())

    collaboration._synthesize_legal_results(
        _mock_contributions(),
        "任务描述",
    )

    assert len(llm.prompts) == 1
    return llm.prompts[0]


def _generic_degraded_result(lang: str):
    collaboration = MultiAgentCollaboration(
        llm_client=_FailingLLM(),
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        lang=lang,
    )
    collaboration.register_agent(_reviewer())
    return collaboration._synthesize_results(
        _mock_contributions(),
        "原始任务描述",
    )


def _legal_degraded_result(lang: str):
    collaboration = MultiAgentCollaboration(
        llm_client=_FailingLLM(),
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(
            bounded_synthesis=True,
        ),
        lang=lang,
    )
    collaboration.register_agent(_reviewer())
    return collaboration._synthesize_results(
        _mock_contributions(),
        "原始任务描述",
    )


def _legal_collaboration(lang: str = "zh") -> MultiAgentCollaboration:
    return MultiAgentCollaboration(
        llm_client=_RecordingLLM(),
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(
            bounded_synthesis=True,
        ),
        lang=lang,
    )


def _record_context_translation_calls(monkeypatch):
    translations = {
        "synthesis.legal.context.original_task_label": "原始任务:",
        "synthesis.legal.context.limitations_label": "结果局限:",
        "synthesis.legal.context.failed_agents_prefix": (
            "以下 Agent 执行失败，未纳入专业成果："
        ),
        "synthesis.legal.context.failed_agents_separator": "、",
    }
    calls = []

    def fake_translate(key, lang):
        calls.append((key, lang))
        return translations[key]

    monkeypatch.setattr(collaboration_module, "translate", fake_translate)
    return calls


def _record_degraded_translation_calls(monkeypatch):
    real_translate = collaboration_module.translate
    translations = {
        "synthesis.legal.degraded_title": "法律多智能体协作降级报告",
        "synthesis.legal.degraded_intro": (
            "最终整合已降级：最终整合模型调用失败，以下内容基于已完成 Agent "
            "的受限摘录生成，请人工复核。"
        ),
        "synthesis.legal.degraded_excerpts_heading": "受限成果摘录",
        "synthesis.legal.degraded_empty_excerpts": "无可用成果摘录。",
        "synthesis.legal.human_review_heading": "人工复核提示",
        "synthesis.legal.human_review_body": (
            "本报告不构成正式律师意见，请结合原合同、法律依据和业务背景进行人工复核。"
        ),
    }
    calls = []

    def fake_translate(key, lang):
        if key not in translations:
            return real_translate(key, lang)
        calls.append((key, lang))
        return translations[key]

    monkeypatch.setattr(collaboration_module, "translate", fake_translate)
    return calls


def test_generic_synthesis_prompt_zh_no_suffix():
    prompt = _record_synthesis_prompt("zh")

    assert "## Output Language" not in prompt
    assert "作为协调者" in prompt
    assert "原始任务：\n原始任务描述" in prompt
    assert "请整合以上内容" in prompt


def test_generic_synthesis_prompt_en_has_english_suffix():
    prompt = _record_synthesis_prompt("en")
    en_suffix = build_llm_language_suffix("en")

    assert prompt.endswith(en_suffix)
    assert "## Output Language" in prompt


def test_generic_synthesis_prompt_ru_has_russian_suffix():
    prompt = _record_synthesis_prompt("ru")

    assert "русском" in prompt
    assert "## Язык ответа" in prompt


def test_generic_synthesis_prompt_unsupported_lang_falls_back_en():
    prompt_ja = _record_synthesis_prompt("ja")
    prompt_en = _record_synthesis_prompt("en")
    en_suffix = build_llm_language_suffix("en")

    assert prompt_ja.endswith(en_suffix)
    assert prompt_ja == prompt_en


def test_generic_degraded_report_zh():
    collaboration = MultiAgentCollaboration(
        llm_client=_FailingLLM(),
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        lang="zh",
    )
    collaboration.register_agent(_reviewer())

    result = collaboration._synthesize_results(
        _mock_contributions(),
        "原始任务描述",
    )

    assert result.status == "degraded"
    assert "# 协作结果" in result.output
    assert "原始任务：" in result.output
    assert "reviewer" in result.output


def test_generic_degraded_report_en():
    result = _generic_degraded_result("en")

    assert result.status == "degraded"
    assert "# Collaboration Result" in result.output
    assert "Original Task:" in result.output


def test_generic_degraded_report_ru():
    result = _generic_degraded_result("ru")

    assert result.status == "degraded"
    assert "# Результат совместной работы" in result.output
    assert "Исходная задача:" in result.output


def test_generic_degraded_report_unsupported_lang_falls_back_en():
    result_ja = _generic_degraded_result("ja")
    result_en = _generic_degraded_result("en")

    assert result_ja.status == "degraded"
    assert result_ja.output == result_en.output


def test_legal_synthesis_prompt_zh_no_suffix():
    prompt = _record_legal_synthesis_prompt("zh")

    assert "## Output Language" not in prompt
    assert "中文" not in prompt
    assert "请输出结构清晰的 Markdown，并保留人工复核提示。" in prompt
    assert "BEGIN_UNTRUSTED_AGENT_RESULTS" in prompt
    assert "END_UNTRUSTED_AGENT_RESULTS" in prompt


def test_legal_synthesis_prompt_en_has_english_suffix():
    prompt = _record_legal_synthesis_prompt("en")
    en_suffix = build_llm_language_suffix("en")

    assert "## Output Language" in prompt
    assert "中文" not in prompt
    assert prompt.endswith(en_suffix)


def test_legal_synthesis_prompt_ru_has_russian_suffix():
    prompt = _record_legal_synthesis_prompt("ru")

    assert "русском" in prompt
    assert "## Язык ответа" in prompt


def test_legal_synthesis_prompt_unsupported_lang_falls_back_en():
    prompt_ja = _record_legal_synthesis_prompt("ja")
    prompt_en = _record_legal_synthesis_prompt("en")
    en_suffix = build_llm_language_suffix("en")

    assert prompt_ja.endswith(en_suffix)
    assert prompt_ja == prompt_en


def test_legal_context_original_task_label_zh(monkeypatch):
    calls = _record_context_translation_calls(monkeypatch)
    collaboration = _legal_collaboration(lang="zh")

    context = collaboration._build_legal_synthesis_context({}, "任务A")

    assert "原始任务:\n任务A" in context
    assert (
        "synthesis.legal.context.original_task_label",
        "zh",
    ) in calls


def test_legal_context_limitations_label_zh_when_failed_agents(monkeypatch):
    calls = _record_context_translation_calls(monkeypatch)
    collaboration = _legal_collaboration(lang="zh")
    collaboration.register_agents(
        [_reviewer("reviewer_a"), _reviewer("reviewer_b")]
    )
    contributions = {
        "reviewer_a": {"response": "", "status": "failed"},
        "reviewer_b": {"response": "", "status": "failed"},
    }

    context = collaboration._build_legal_synthesis_context(
        contributions,
        "任务A",
    )

    assert "结果局限:" in context
    assert "以下 Agent 执行失败，未纳入专业成果：reviewer_a、reviewer_b" in context
    assert (
        "synthesis.legal.context.limitations_label",
        "zh",
    ) in calls
    assert (
        "synthesis.legal.context.failed_agents_prefix",
        "zh",
    ) in calls
    assert (
        "synthesis.legal.context.failed_agents_separator",
        "zh",
    ) in calls


def test_legal_context_agent_role_header_stable():
    collaboration = _legal_collaboration(lang="zh")
    collaboration.register_agent(_reviewer())

    context = collaboration._build_legal_synthesis_context(
        _mock_contributions(),
        "任务A",
    )

    assert "### reviewer (specialist)" in context


def test_legal_context_original_task_label_en():
    context = _legal_collaboration(lang="en")._build_legal_synthesis_context(
        {},
        "Task A",
    )

    assert "Original Task:\nTask A" in context


def test_legal_context_original_task_label_ru():
    context = _legal_collaboration(lang="ru")._build_legal_synthesis_context(
        {},
        "Задача A",
    )

    assert "Исходная задача:\nЗадача A" in context


def test_legal_context_limitations_label_en():
    collaboration = _legal_collaboration(lang="en")
    collaboration.register_agents(
        [_reviewer("reviewer_a"), _reviewer("reviewer_b")]
    )
    context = collaboration._build_legal_synthesis_context(
        {
            "reviewer_a": {"response": "", "status": "failed"},
            "reviewer_b": {"response": "", "status": "failed"},
        },
        "Task A",
    )

    assert "Result Limitations:" in context
    assert (
        "The following agents failed to complete and are excluded from "
        "professional results: reviewer_a, reviewer_b"
    ) in context


def test_legal_context_limitations_label_ru():
    collaboration = _legal_collaboration(lang="ru")
    collaboration.register_agents(
        [_reviewer("reviewer_a"), _reviewer("reviewer_b")]
    )
    context = collaboration._build_legal_synthesis_context(
        {
            "reviewer_a": {"response": "", "status": "failed"},
            "reviewer_b": {"response": "", "status": "failed"},
        },
        "Задача A",
    )

    assert "Ограничения результата:" in context
    assert (
        "Следующие агенты не завершили выполнение и исключены из "
        "профессиональных результатов: reviewer_a, reviewer_b"
    ) in context


def test_legal_degraded_report_zh_preserves_p0_output(monkeypatch):
    calls = _record_degraded_translation_calls(monkeypatch)
    collaboration = MultiAgentCollaboration(
        llm_client=_FailingLLM(),
        mode=CollaborationMode.SEQUENTIAL,
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(
            bounded_synthesis=True,
        ),
        lang="zh",
    )
    collaboration.register_agent(_reviewer())

    result = collaboration._synthesize_results(
        _mock_contributions(),
        "原始任务描述",
    )

    assert result.status == "degraded"
    assert "# 法律多智能体协作降级报告" in result.output
    assert (
        "最终整合已降级：最终整合模型调用失败，以下内容基于已完成 Agent "
        "的受限摘录生成，请人工复核。"
    ) in result.output
    assert "## 受限成果摘录" in result.output
    assert "## 人工复核提示" in result.output
    assert (
        "本报告不构成正式律师意见，请结合原合同、法律依据和业务背景进行人工复核。"
    ) in result.output
    assert calls == [
        ("synthesis.legal.degraded_title", "zh"),
        ("synthesis.legal.degraded_intro", "zh"),
        ("synthesis.legal.degraded_excerpts_heading", "zh"),
        ("synthesis.legal.degraded_empty_excerpts", "zh"),
        ("synthesis.legal.human_review_heading", "zh"),
        ("synthesis.legal.human_review_body", "zh"),
    ]


def test_legal_degraded_report_empty_context_zh(monkeypatch):
    calls = _record_degraded_translation_calls(monkeypatch)
    collaboration = _legal_collaboration(lang="zh")

    output = collaboration._build_legal_degraded_synthesis_report("")

    assert "无可用成果摘录。" in output
    assert ("synthesis.legal.degraded_empty_excerpts", "zh") in calls


def test_legal_degraded_report_en():
    result = _legal_degraded_result("en")

    assert result.status == "degraded"
    assert "# Legal Multi-Agent Collaboration Fallback Report" in result.output
    assert "## Bounded Result Excerpts" in result.output
    assert "## Human Review Notice" in result.output
    assert "This report does not constitute formal legal counsel." in result.output


def test_legal_degraded_report_ru():
    result = _legal_degraded_result("ru")

    assert result.status == "degraded"
    assert (
        "# Отчёт о резервной работе юридической мульти-агентной системы"
        in result.output
    )
    assert "## Ограниченные выдержки результатов" in result.output
    assert "## Уведомление о проверке специалистом" in result.output
    assert (
        "Настоящий отчёт не является официальным юридическим заключением."
        in result.output
    )


def test_legal_human_review_body_en_preserves_compliance_semantics():
    body = translate("synthesis.legal.human_review_body", "en").lower()

    assert "does not constitute formal legal counsel" in body
    assert all(
        term in body
        for term in ("original contract", "legal basis", "business context")
    )
    assert "human review" in body


def test_legal_human_review_body_ru_preserves_compliance_semantics():
    body = translate("synthesis.legal.human_review_body", "ru").lower()

    assert "не является официальным юридическим заключением" in body
    assert all(
        term in body
        for term in ("исходного договора", "правовой базы", "бизнес-контекста")
    )
    assert "проверка специалистом" in body


def test_legal_human_review_body_en_contains_formal_legal_counsel_phrase():
    body = translate("synthesis.legal.human_review_body", "en").lower()

    assert "does not constitute formal legal counsel" in body


def test_legal_human_review_body_ru_contains_formal_legal_counsel_phrase():
    body = translate("synthesis.legal.human_review_body", "ru")

    assert "не является официальным юридическим заключением" in body


def test_legal_human_review_body_en_contains_three_elements():
    body = translate("synthesis.legal.human_review_body", "en").lower()

    assert "original contract" in body
    assert "legal basis" in body
    assert "business context" in body


def test_legal_human_review_body_ru_contains_three_elements():
    body = translate("synthesis.legal.human_review_body", "ru")

    assert "исходного договора" in body
    assert "правовой базы" in body
    assert "бизнес-контекста" in body


def test_legal_human_review_body_en_contains_human_review():
    body = translate("synthesis.legal.human_review_body", "en").lower()

    assert "human review" in body


def test_legal_human_review_body_ru_contains_human_review():
    body = translate("synthesis.legal.human_review_body", "ru")

    assert "проверка специалистом" in body


def test_synthesis_result_metadata_defaults_empty():
    result = SynthesisResult(output="ok", status="completed")

    assert result.metadata == {}


def test_language_guard_failed_report_is_deterministic_and_does_not_leak():
    collaboration = _legal_collaboration(lang="ru")

    output = collaboration._build_language_guard_failed_report()

    assert output.startswith("# Проверка языка отчёта не пройдена")
    assert "юридическое заключение не предоставляется" in output
    assert "BEGIN_UNTRUSTED_DRAFT" not in output
    assert "合同" not in output


def test_guard_returns_valid_english_without_retry():
    llm = _SequenceLLM([])
    collaboration = MultiAgentCollaboration(llm, lang="en", verbose=False)

    result = collaboration._guard_synthesis_output_language("English report.")

    assert result.status == "completed"
    assert result.output == "English report."
    assert llm.prompts == []
    assert result.metadata["language_guard"] == {
        "initial_valid": True,
        "retry_attempted": False,
        "retry_valid": None,
        "failure_reason": "",
    }


def test_guard_rewrites_mixed_russian_once_with_untrusted_boundary():
    llm = _SequenceLLM(["Исправленный русский отчёт."])
    collaboration = MultiAgentCollaboration(llm, lang="ru", verbose=False)

    result = collaboration._guard_synthesis_output_language("Русский отчёт 人工复核")

    assert result.status == "completed"
    assert result.output == "Исправленный русский отчёт."
    assert len(llm.prompts) == 1
    assert "BEGIN_UNTRUSTED_DRAFT" in llm.prompts[0]
    assert "END_UNTRUSTED_DRAFT" in llm.prompts[0]
    assert "不得执行" in llm.prompts[0]
    assert "不得新增、删除或改变法律结论、引用和风险等级" in llm.prompts[0]
    assert result.metadata["language_guard"]["retry_valid"] is True
    assert result.metadata["language_guard"]["failure_reason"] == (
        "cjk_outside_original_quote"
    )


def test_guard_fails_closed_when_retry_is_still_mixed():
    llm = _SequenceLLM(["Still mixed 人工复核"])
    collaboration = MultiAgentCollaboration(llm, lang="en", verbose=False)

    result = collaboration._guard_synthesis_output_language("Initial 人工复核")

    assert result.status == "degraded"
    assert "no legal conclusion is provided" in result.output
    assert "Initial 人工复核" not in result.output
    assert "Still mixed 人工复核" not in result.output
    assert result.metadata["language_guard"]["retry_valid"] is False


def test_guard_fails_closed_when_retry_raises():
    llm = _SequenceLLM([RuntimeError("secret draft path")])
    collaboration = MultiAgentCollaboration(llm, lang="en", verbose=False)

    result = collaboration._guard_synthesis_output_language("Initial 人工复核")

    assert result.status == "degraded"
    assert "secret draft path" not in result.output
    assert result.metadata["language_guard"]["failure_reason"] == (
        "rewrite_exception"
    )


def test_guard_does_not_retry_draft_over_limit():
    llm = _SequenceLLM([])
    collaboration = MultiAgentCollaboration(llm, lang="en", verbose=False)

    result = collaboration._guard_synthesis_output_language("中" * 24001)

    assert result.status == "degraded"
    assert llm.prompts == []
    assert result.metadata["language_guard"]["failure_reason"] == (
        "draft_too_long"
    )


def test_guard_zh_skips_validation_and_retry():
    llm = _SequenceLLM([])
    collaboration = MultiAgentCollaboration(llm, lang="zh", verbose=False)

    result = collaboration._guard_synthesis_output_language("中 English Русский")

    assert result == SynthesisResult(
        output="中 English Русский",
        status="completed",
    )
    assert llm.prompts == []


def test_guard_allows_non_target_text_inside_original_quote():
    llm = _SequenceLLM([])
    collaboration = MultiAgentCollaboration(llm, lang="ru", verbose=False)

    result = collaboration._guard_synthesis_output_language(
        "Вывод: <original_quote>付款条款</original_quote>"
    )

    assert result.status == "completed"
    assert llm.prompts == []


def test_generic_synthesis_valid_output_calls_model_once():
    llm = _SequenceLLM(["English final report."])
    collaboration = MultiAgentCollaboration(llm, lang="en", verbose=False)

    result = collaboration._synthesize_results(_mock_contributions(), "Task")

    assert result.status == "completed"
    assert len(llm.prompts) == 1
    assert result.metadata["language_guard"]["initial_valid"] is True


def test_generic_synthesis_mixed_output_rewrites_once():
    llm = _SequenceLLM(["English 人工复核", "Rewritten English report."])
    collaboration = MultiAgentCollaboration(llm, lang="en", verbose=False)

    result = collaboration._synthesize_results(_mock_contributions(), "Task")

    assert result.output == "Rewritten English report."
    assert len(llm.prompts) == 2


def test_legal_synthesis_mixed_output_rewrites_once():
    llm = _SequenceLLM(["Русский 人工复核", "Исправленный русский отчёт."])
    collaboration = MultiAgentCollaboration(
        llm,
        lang="ru",
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(
            bounded_synthesis=True,
        ),
    )

    result = collaboration._synthesize_legal_results(
        _mock_contributions(),
        "Задача",
    )

    assert result.output == "Исправленный русский отчёт."
    assert len(llm.prompts) == 2


def test_legal_synthesis_two_mixed_outputs_returns_safe_notice():
    llm = _SequenceLLM(["Русский 人工复核", "Всё ещё 人工复核"])
    collaboration = MultiAgentCollaboration(
        llm,
        lang="ru",
        verbose=False,
        execution_policy=LegalCollaborationExecutionPolicy(
            bounded_synthesis=True,
        ),
    )

    result = collaboration._synthesize_legal_results(
        _mock_contributions(),
        "Задача",
    )

    assert result.status == "degraded"
    assert "юридическое заключение не предоставляется" in result.output
    assert "人工复核" not in result.output


def test_generic_first_synthesis_exception_keeps_existing_degraded_report():
    result = _generic_degraded_result("en")

    assert result.status == "degraded"
    assert "# Collaboration Result" in result.output
    assert result.metadata == {}


def test_legal_first_synthesis_exception_keeps_existing_degraded_report():
    result = _legal_degraded_result("ru")

    assert result.status == "degraded"
    assert result.output.startswith(
        "# Отчёт о резервной работе юридической мульти-агентной системы"
    )
    assert result.metadata == {}

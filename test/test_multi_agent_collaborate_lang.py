"""多智能体协作 prompt 输出语言后缀测试。"""

from shuyixiao_agent.agents.multi_agent_collaboration import (
    AgentProfile,
    AgentRole,
    CollaborationMode,
    MultiAgentCollaboration,
)


class _RecordingLLM:
    def __init__(self):
        self.prompts: list[str] = []

    def simple_chat(self, prompt, timeout=None):
        self.prompts.append(prompt)
        return "ok"


def _agent() -> AgentProfile:
    return AgentProfile(
        name="reviewer",
        role=AgentRole.SPECIALIST,
        description="审查合同条款",
        expertise=["合同审查"],
        system_prompt="你是一名合同审查专家。",
    )


def _collaboration(lang=None, llm=None) -> MultiAgentCollaboration:
    kwargs = {
        "llm_client": llm or _RecordingLLM(),
        "mode": CollaborationMode.SEQUENTIAL,
        "verbose": False,
    }
    if lang is not None:
        kwargs["lang"] = lang
    return MultiAgentCollaboration(**kwargs)


def test_lang_zh_prompt_no_suffix():
    collaboration = _collaboration(lang="zh")

    prompt = collaboration._build_agent_prompt(_agent(), "检查付款条款", None)

    assert "## Output Language" not in prompt
    assert prompt == "你是一名合同审查专家。\n\n## 任务\n检查付款条款\n\n请提供你的专业见解："


def test_lang_en_prompt_has_english_suffix():
    collaboration = _collaboration(lang="en")

    prompt = collaboration._build_agent_prompt(_agent(), "检查付款条款", None)

    assert "## Output Language" in prompt
    assert "English" in prompt
    assert prompt.endswith("Cyrillic characters outside those tags.")


def test_lang_ru_prompt_has_russian_suffix():
    collaboration = _collaboration(lang="ru")

    prompt = collaboration._build_agent_prompt(_agent(), "检查付款条款", None)

    assert "## Язык ответа" in prompt
    assert "русском" in prompt


def test_default_lang_is_zh():
    default_collaboration = _collaboration()
    zh_collaboration = _collaboration(lang="zh")

    default_prompt = default_collaboration._build_agent_prompt(
        _agent(), "检查付款条款", None
    )
    zh_prompt = zh_collaboration._build_agent_prompt(_agent(), "检查付款条款", None)

    assert default_collaboration.lang == "zh"
    assert default_prompt == zh_prompt


def test_lang_passed_via_collaborate():
    llm = _RecordingLLM()
    collaboration = _collaboration(lang="en", llm=llm)
    collaboration.register_agent(_agent())

    result = collaboration.collaborate("检查付款条款")

    assert result.success is True
    assert "## Output Language" in llm.prompts[0]
    assert "English" in llm.prompts[0]


def test_lang_unsupported_falls_back_en_in_prompt():
    unsupported_prompt = _collaboration(lang="ja")._build_agent_prompt(
        _agent(), "检查付款条款", None
    )
    en_prompt = _collaboration(lang="en")._build_agent_prompt(
        _agent(), "检查付款条款", None
    )

    assert unsupported_prompt == en_prompt

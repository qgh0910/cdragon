"""静态翻译表模块基础测试。"""

from importlib import import_module
import re
from types import ModuleType

import pytest


KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
PLACEHOLDERS = ("TODO", "待翻译", "???")
LEGAL_AGENT_PREFIXES = (
    "agent.contract_reviewer",
    "agent.clause_risk_analyzer",
    "agent.legal_researcher",
    "agent.drafting_specialist",
    "agent.compliance_checker",
    "agent.audit_recorder",
)
MODE_PREFIXES = (
    "mode.sequential",
    "mode.parallel",
    "mode.hierarchical",
    "mode.peer_to_peer",
    "mode.hybrid",
)


def _load_messages() -> ModuleType:
    """在用例执行期加载 Step 4 待实现的模块。"""
    try:
        return import_module("shuyixiao_agent.i18n.messages")
    except ModuleNotFoundError as exc:
        if exc.name == "shuyixiao_agent.i18n.messages":
            pytest.fail("messages module is not implemented yet", pytrace=False)
        raise


def test_messages_module_importable():
    assert _load_messages() is not None


def test_supported_langs_includes_zh_en_ru():
    messages = _load_messages()

    assert set(messages.SUPPORTED_LANGS) == {"en", "zh", "ru"}


def test_default_lang_is_zh():
    messages = _load_messages()

    assert messages.DEFAULT_LANG == "zh"


def test_all_keys_have_three_langs():
    messages = _load_messages()
    expected_langs = set(messages.SUPPORTED_LANGS)
    invalid = {
        key: sorted(set(translations) ^ expected_langs)
        for key, translations in messages.MESSAGES.items()
        if set(translations) != expected_langs
    }

    assert invalid == {}, f"翻译 key 的语言集合不完整: {invalid}"


def test_all_values_non_empty():
    messages = _load_messages()
    invalid = [
        f"{key}:{lang}"
        for key, translations in messages.MESSAGES.items()
        for lang, value in translations.items()
        if not isinstance(value, str) or not value.strip()
    ]

    assert invalid == [], f"翻译值为空或不是字符串: {invalid}"


def test_all_keys_match_naming_regex():
    messages = _load_messages()
    invalid = [
        key for key in messages.MESSAGES if not KEY_PATTERN.fullmatch(key)
    ]

    assert invalid == [], f"翻译 key 命名不合规: {invalid}"


def test_no_placeholder_strings():
    messages = _load_messages()
    invalid = [
        f"{key}:{lang}:{placeholder}"
        for key, translations in messages.MESSAGES.items()
        for lang, value in translations.items()
        for placeholder in PLACEHOLDERS
        if placeholder in value
    ]

    assert invalid == [], f"翻译值仍含占位符: {invalid}"


def test_legal_agents_have_full_translations():
    messages = _load_messages()
    expected_keys = {
        key
        for prefix in LEGAL_AGENT_PREFIXES
        for key in (
            f"{prefix}.name",
            f"{prefix}.description",
            *(f"{prefix}.expertise.{index}" for index in range(4)),
        )
    }
    missing = sorted(expected_keys - set(messages.MESSAGES))

    assert missing == [], f"法律 Agent 翻译 key 缺失: {missing}"
    assert all(
        set(messages.MESSAGES[key]) == set(messages.SUPPORTED_LANGS)
        for key in expected_keys
    )


def test_modes_have_full_translations():
    messages = _load_messages()
    expected_keys = {
        f"{prefix}.{field}"
        for prefix in MODE_PREFIXES
        for field in ("name", "description", "use_case")
    }
    missing = sorted(expected_keys - set(messages.MESSAGES))

    assert missing == [], f"协作模式翻译 key 缺失: {missing}"
    assert all(
        set(messages.MESSAGES[key]) == set(messages.SUPPORTED_LANGS)
        for key in expected_keys
    )

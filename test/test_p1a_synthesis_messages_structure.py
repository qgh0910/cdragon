"""P1a synthesis 翻译 key 的结构约束测试。"""

import re

from shuyixiao_agent.i18n.messages import MESSAGES


KEY_PATTERN = re.compile(r"^synthesis\.[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
EXPECTED_LANGS = {"en", "zh", "ru"}


def _assert_key_exists(key: str) -> None:
    assert key in MESSAGES, f"缺少 synthesis 翻译 key: {key}"


def test_key_synthesis_generic_degraded_title_exists():
    _assert_key_exists("synthesis.generic.degraded_title")


def test_key_synthesis_generic_original_task_label_exists():
    _assert_key_exists("synthesis.generic.original_task_label")


def test_key_synthesis_legal_degraded_title_exists():
    _assert_key_exists("synthesis.legal.degraded_title")


def test_key_synthesis_legal_degraded_intro_exists():
    _assert_key_exists("synthesis.legal.degraded_intro")


def test_key_synthesis_legal_degraded_excerpts_heading_exists():
    _assert_key_exists("synthesis.legal.degraded_excerpts_heading")


def test_key_synthesis_legal_degraded_empty_excerpts_exists():
    _assert_key_exists("synthesis.legal.degraded_empty_excerpts")


def test_key_synthesis_legal_human_review_heading_exists():
    _assert_key_exists("synthesis.legal.human_review_heading")


def test_key_synthesis_legal_human_review_body_exists():
    _assert_key_exists("synthesis.legal.human_review_body")


def test_key_synthesis_legal_context_original_task_label_exists():
    _assert_key_exists("synthesis.legal.context.original_task_label")


def test_key_synthesis_legal_context_limitations_label_exists():
    _assert_key_exists("synthesis.legal.context.limitations_label")


def test_key_synthesis_legal_context_failed_agents_prefix_exists():
    _assert_key_exists("synthesis.legal.context.failed_agents_prefix")


def test_key_synthesis_legal_context_failed_agents_separator_exists():
    _assert_key_exists("synthesis.legal.context.failed_agents_separator")


def test_key_synthesis_language_guard_failed_title_exists():
    _assert_key_exists("synthesis.language_guard.failed_title")


def test_key_synthesis_language_guard_failed_body_exists():
    _assert_key_exists("synthesis.language_guard.failed_body")


def test_all_synthesis_keys_have_three_langs():
    synthesis_entries = {
        key: translations
        for key, translations in MESSAGES.items()
        if key.startswith("synthesis.")
    }
    invalid = {
        key: sorted(set(translations) ^ EXPECTED_LANGS)
        for key, translations in synthesis_entries.items()
        if set(translations) != EXPECTED_LANGS
    }

    assert invalid == {}, f"synthesis 翻译 key 的语言集合不完整: {invalid}"


def test_all_synthesis_keys_match_naming_regex():
    invalid = [
        key
        for key in MESSAGES
        if key.startswith("synthesis.") and not KEY_PATTERN.fullmatch(key)
    ]

    assert invalid == [], f"synthesis 翻译 key 命名不合规: {invalid}"


def test_language_guard_failed_body_preserves_safe_semantics():
    expected_terms = {
        "en": ("no legal conclusion", "retry", "human review"),
        "zh": ("未提供法律结论", "重试", "人工复核"),
        "ru": (
            "юридическое заключение не предоставляется",
            "Повторите",
            "проверку специалистом",
        ),
    }

    body = MESSAGES["synthesis.language_guard.failed_body"]
    for lang, terms in expected_terms.items():
        assert all(term in body[lang] for term in terms)

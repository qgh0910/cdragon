"""LLM 输出语言指令单元测试。"""

from shuyixiao_agent.i18n.llm_instructions import build_llm_language_suffix


def test_zh_returns_empty_string():
    assert build_llm_language_suffix("zh") == ""


def test_en_returns_english_instruction():
    assert "English" in build_llm_language_suffix("en")


def test_ru_returns_russian_instruction():
    assert "русском" in build_llm_language_suffix("ru")


def test_unsupported_falls_back_to_en():
    assert build_llm_language_suffix("ja") == build_llm_language_suffix("en")


def test_suffix_starts_with_double_newline():
    for lang in ("en", "ru"):
        assert build_llm_language_suffix(lang).startswith("\n\n")

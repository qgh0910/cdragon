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


def test_en_suffix_requires_target_language_outside_original_quotes():
    suffix = build_llm_language_suffix("en")

    assert "Write all titles, analysis, conclusions" in suffix
    assert "recommendations, and disclaimers" in suffix
    assert "<original_quote>" in suffix
    assert "outside" in suffix
    assert "CJK or Cyrillic" in suffix


def test_ru_suffix_requires_target_language_outside_original_quotes():
    suffix = build_llm_language_suffix("ru")

    assert "Все заголовки, анализ, выводы" in suffix
    assert "рекомендации и оговорки" in suffix
    assert "<original_quote>" in suffix
    assert "Вне" in suffix
    assert "кириллицу" in suffix


def test_zh_suffix_remains_empty_after_quote_rule_change():
    assert build_llm_language_suffix("zh") == ""

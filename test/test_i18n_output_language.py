"""最终报告输出语言校验测试。"""

import pytest

from shuyixiao_agent.i18n.output_language import validate_output_language


@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("Contract review completed.", "en"),
        ("Evidence: <original_quote>付款条款</original_quote>", "en"),
        ("Проверка договора завершена.", "ru"),
        ("Доказательство: <original_quote>付款条款</original_quote>", "ru"),
        ("任意中文报告", "zh"),
        ("English fallback output.", "ja"),
    ],
)
def test_valid_output_languages(text, lang):
    assert validate_output_language(text, lang).is_valid is True


@pytest.mark.parametrize(
    ("text", "lang", "reason"),
    [
        ("English conclusion 人工复核", "en", "cjk_outside_original_quote"),
        ("English conclusion риск", "en", "cyrillic_outside_original_quote"),
        ("1234 --", "en", "missing_latin"),
        ("Русский вывод 人工复核", "ru", "cjk_outside_original_quote"),
        ("English only conclusion", "ru", "missing_cyrillic"),
        ("中文 fallback", "ja", "cjk_outside_original_quote"),
        ("", "en", "empty_output"),
        ("   ", "ru", "empty_output"),
        ("English <original_quote>中文", "en", "unpaired_original_quote_tag"),
        ("Русский </original_quote>", "ru", "unpaired_original_quote_tag"),
    ],
)
def test_invalid_output_languages(text, lang, reason):
    result = validate_output_language(text, lang)

    assert result.is_valid is False
    assert result.reason == reason


def test_multiple_original_quote_blocks_are_ignored():
    text = (
        "Evidence A <original_quote>付款</original_quote> and evidence B "
        "<original_quote>违约责任</original_quote>."
    )

    assert validate_output_language(text, "en").is_valid is True

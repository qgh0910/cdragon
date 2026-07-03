"""LLM 输出语言指令模板。"""

LLM_LANGUAGE_INSTRUCTIONS = {
    "en": (
        "\n\n"
        "## Output Language\n"
        "Write all titles, analysis, conclusions, risk levels, recommendations, "
        "and disclaimers in **English** using precise legal terminology. "
        "Only verbatim contract clauses, party names, and legal citations may "
        "remain in another language, and every such passage must be enclosed in "
        "paired <original_quote>...</original_quote> tags. Do not use CJK or "
        "Cyrillic characters outside those tags."
    ),
    "ru": (
        "\n\n"
        "## Язык ответа\n"
        "Все заголовки, анализ, выводы, уровни риска, рекомендации и оговорки "
        "пишите на **русском языке**, используя точную юридическую терминологию. "
        "На другом языке допускаются только дословные пункты договора, имена "
        "сторон и правовые ссылки; каждый такой фрагмент заключайте в парные "
        "теги <original_quote>...</original_quote>. Вне этих тегов используйте "
        "кириллицу и не используйте китайские иероглифы."
    ),
    "zh": "",
}


def build_llm_language_suffix(lang: str) -> str:
    """返回目标语言的 LLM 输出指令,不支持的语言回落到英文。"""
    return LLM_LANGUAGE_INSTRUCTIONS.get(lang.lower(), LLM_LANGUAGE_INSTRUCTIONS["en"])

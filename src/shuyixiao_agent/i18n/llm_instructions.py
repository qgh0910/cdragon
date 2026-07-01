"""LLM 输出语言指令模板。"""

LLM_LANGUAGE_INSTRUCTIONS = {
    "en": (
        "\n\n"
        "## Output Language\n"
        "Please respond in **English**. Use precise legal terminology. "
        "Keep contract clauses, party names and citations in their original language "
        "if a verbatim quote is required."
    ),
    "ru": (
        "\n\n"
        "## Язык ответа\n"
        "Пожалуйста, отвечайте на **русском языке**. "
        "Используйте точную юридическую терминологию. "
        "Сохраняйте оригинальный язык для дословного цитирования пунктов договора, "
        "имён сторон и ссылок."
    ),
    "zh": "",
}


def build_llm_language_suffix(lang: str) -> str:
    """返回目标语言的 LLM 输出指令,不支持的语言回落到英文。"""
    return LLM_LANGUAGE_INSTRUCTIONS.get(lang.lower(), LLM_LANGUAGE_INSTRUCTIONS["en"])

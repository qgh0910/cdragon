"""最终报告输出语言的确定性校验。"""

import re
from dataclasses import dataclass


_ORIGINAL_QUOTE_RE = re.compile(
    r"<original_quote>.*?</original_quote>",
    re.DOTALL,
)
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
_LATIN_RE = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class OutputLanguageValidation:
    is_valid: bool
    reason: str = ""


def _narrative_text(text: str) -> tuple[str, str]:
    narrative = _ORIGINAL_QUOTE_RE.sub("", text)
    if "<original_quote>" in narrative or "</original_quote>" in narrative:
        return "", "unpaired_original_quote_tag"
    return narrative, ""


def validate_output_language(
    text: str,
    lang: str,
) -> OutputLanguageValidation:
    if not text or not text.strip():
        return OutputLanguageValidation(False, "empty_output")

    normalized_lang = (
        lang.lower() if lang.lower() in {"en", "zh", "ru"} else "en"
    )
    if normalized_lang == "zh":
        return OutputLanguageValidation(True)

    narrative, quote_error = _narrative_text(text)
    if quote_error:
        return OutputLanguageValidation(False, quote_error)
    if _CJK_RE.search(narrative):
        return OutputLanguageValidation(False, "cjk_outside_original_quote")

    if normalized_lang == "en":
        if _CYRILLIC_RE.search(narrative):
            return OutputLanguageValidation(False, "cyrillic_outside_original_quote")
        if not _LATIN_RE.search(narrative):
            return OutputLanguageValidation(False, "missing_latin")
    elif not _CYRILLIC_RE.search(narrative):
        return OutputLanguageValidation(False, "missing_cyrillic")

    return OutputLanguageValidation(True)

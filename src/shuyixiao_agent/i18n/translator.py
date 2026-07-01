"""后端静态文案翻译。"""

import logging
from typing import Optional

from .messages import DEFAULT_LANG, MESSAGES, SUPPORTED_LANGS

logger = logging.getLogger(__name__)

_MESSAGES = MESSAGES


def _normalize_lang(lang: str) -> str:
    """将语言归一化为受支持的语言代码。"""
    normalized = lang.lower()
    if normalized in SUPPORTED_LANGS:
        return normalized

    logger.warning("Unsupported lang %r, fallback to 'en'", lang)
    return "en"


def _find_translation(key: str, lang: str) -> Optional[str]:
    """查找翻译,目标语言缺失时回落到中文。"""
    translations = _MESSAGES.get(key)
    if translations is None:
        logger.warning("Missing translation key %r", key)
        return None

    normalized = _normalize_lang(lang)
    translated = translations.get(normalized)
    if translated is not None:
        return translated

    logger.warning(
        "Translation %r missing for lang %r, fallback to zh",
        key,
        normalized,
    )
    return translations.get(DEFAULT_LANG)


def translate(key: str, lang: str, fallback: Optional[str] = None) -> str:
    """返回翻译,完全缺失时返回显式 fallback 或 key。"""
    translated = _find_translation(key, lang)
    if translated is not None:
        return translated
    if fallback is not None:
        return fallback
    return key


def translate_or_none(key: str, lang: str) -> Optional[str]:
    """返回翻译,完全缺失时返回 None。"""
    return _find_translation(key, lang)

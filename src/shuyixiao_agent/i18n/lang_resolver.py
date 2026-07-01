"""从 HTTP 请求头解析用户语言。"""

import logging

from starlette.requests import Request

logger = logging.getLogger(__name__)

_SUPPORTED_LANGS = {"en", "zh", "ru"}
_DEFAULT_LANG = "zh"


def _parse_accept_language(value: str) -> str:
    """返回 Accept-Language 中 q 值最高的受支持语言。"""
    candidates: list[tuple[float, int, str]] = []

    for index, item in enumerate(value.split(",")):
        sections = [section.strip() for section in item.split(";")]
        if not sections[0]:
            raise ValueError("empty language range")

        lang = sections[0].split("-", maxsplit=1)[0].lower()
        quality = 1.0
        for parameter in sections[1:]:
            if not parameter:
                raise ValueError("empty Accept-Language parameter")
            name, separator, raw_value = parameter.partition("=")
            if name.strip().lower() == "q":
                if not separator:
                    raise ValueError("missing q value")
                quality = float(raw_value)
                if not 0 <= quality <= 1:
                    raise ValueError("q value outside valid range")

        if lang in _SUPPORTED_LANGS:
            candidates.append((quality, index, lang))

    if not candidates:
        return _DEFAULT_LANG

    candidates.sort(key=lambda candidate: (-candidate[0], candidate[1]))
    return candidates[0][2]


def get_user_lang(request: Request) -> str:
    """按 X-User-Lang、Accept-Language、默认语言的顺序解析请求。"""
    explicit_lang = request.headers.get("X-User-Lang")
    if explicit_lang is not None:
        normalized = explicit_lang.strip().lower()
        if normalized in _SUPPORTED_LANGS:
            return normalized
        logger.warning("Unsupported lang %r, fallback to 'en'", explicit_lang)
        return "en"

    accept_language = request.headers.get("Accept-Language")
    if not accept_language:
        logger.debug("No language header supplied, fallback to %r", _DEFAULT_LANG)
        return _DEFAULT_LANG

    try:
        return _parse_accept_language(accept_language)
    except (TypeError, ValueError):
        logger.warning("Malformed Accept-Language header, fallback to %r", _DEFAULT_LANG)
        return _DEFAULT_LANG

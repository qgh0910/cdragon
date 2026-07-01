"""请求语言解析单元测试。"""

from collections.abc import Callable
from typing import Any

import pytest
from starlette.requests import Request


@pytest.fixture
def get_user_lang() -> Callable[[Request], str]:
    """实现模块在 Step 2 创建前，逐用例标记为跳过。"""
    module = pytest.importorskip("shuyixiao_agent.i18n.lang_resolver")
    return module.get_user_lang


@pytest.fixture
def make_request() -> Callable[[dict[str, str]], Request]:
    """根据请求头构造最小 Starlette 请求对象。"""

    def _make(headers: dict[str, str]) -> Request:
        scope: dict[str, Any] = {
            "type": "http",
            "headers": [
                (key.lower().encode(), value.encode())
                for key, value in headers.items()
            ],
        }
        return Request(scope)

    return _make


def test_xuserlang_en(get_user_lang, make_request):
    request = make_request({"X-User-Lang": "en"})

    assert get_user_lang(request) == "en"


def test_xuserlang_zh(get_user_lang, make_request):
    request = make_request({"X-User-Lang": "zh"})

    assert get_user_lang(request) == "zh"


def test_xuserlang_ru(get_user_lang, make_request):
    request = make_request({"X-User-Lang": "ru"})

    assert get_user_lang(request) == "ru"


def test_xuserlang_uppercase_normalized(get_user_lang, make_request):
    request = make_request({"X-User-Lang": "EN"})

    assert get_user_lang(request) == "en"


def test_xuserlang_unsupported_fallback_en(get_user_lang, make_request):
    request = make_request({"X-User-Lang": "ja"})

    assert get_user_lang(request) == "en"


def test_accept_language_only_en(get_user_lang, make_request):
    request = make_request({"Accept-Language": "en-US,en;q=0.9"})

    assert get_user_lang(request) == "en"


def test_accept_language_only_zh_cn(get_user_lang, make_request):
    request = make_request({"Accept-Language": "zh-CN"})

    assert get_user_lang(request) == "zh"


def test_accept_language_mixed_pick_in_whitelist(get_user_lang, make_request):
    request = make_request({"Accept-Language": "ja,en;q=0.5"})

    assert get_user_lang(request) == "en"


def test_no_headers_default_zh(get_user_lang, make_request):
    request = make_request({})

    assert get_user_lang(request) == "zh"


def test_malformed_accept_language(get_user_lang, make_request):
    request = make_request({"Accept-Language": ";;;;"})

    assert get_user_lang(request) == "zh"


def test_xuserlang_takes_precedence(get_user_lang, make_request):
    request = make_request(
        {"X-User-Lang": "ru", "Accept-Language": "en"}
    )

    assert get_user_lang(request) == "ru"

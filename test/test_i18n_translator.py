"""静态翻译函数单元测试。"""

from collections.abc import Callable
from importlib import import_module
from types import ModuleType

import pytest


@pytest.fixture
def load_translator() -> Callable[[], ModuleType]:
    """在用例执行期加载 Step 4 待实现的模块。"""

    def _load() -> ModuleType:
        try:
            return import_module("shuyixiao_agent.i18n.translator")
        except ModuleNotFoundError as exc:
            if exc.name == "shuyixiao_agent.i18n.translator":
                pytest.fail("translator module is not implemented yet", pytrace=False)
            raise

    return _load


@pytest.fixture
def fake_messages() -> dict[str, dict[str, str]]:
    """使翻译逻辑测试不依赖未来的业务翻译表。"""
    return {
        "agent.demo.name": {"en": "Demo", "zh": "演示", "ru": "Демо"},
        "agent.zh_only.name": {"zh": "仅中文"},
    }


def _install_messages(
    translator: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    messages: dict[str, dict[str, str]],
) -> None:
    monkeypatch.setattr(translator, "_MESSAGES", messages)


def test_existing_key_existing_lang_returns_value(
    load_translator, fake_messages, monkeypatch
):
    translator = load_translator()
    _install_messages(translator, monkeypatch, fake_messages)

    assert translator.translate("agent.demo.name", "ru") == "Демо"


def test_existing_key_unsupported_lang_treats_as_en(
    load_translator, fake_messages, monkeypatch
):
    translator = load_translator()
    _install_messages(translator, monkeypatch, fake_messages)

    assert translator.translate("agent.demo.name", "ja") == "Demo"


def test_missing_key_with_fallback_returns_fallback(
    load_translator, fake_messages, monkeypatch
):
    translator = load_translator()
    _install_messages(translator, monkeypatch, fake_messages)

    assert translator.translate("agent.missing.name", "en", fallback="") == ""


def test_missing_key_without_fallback_returns_key(
    load_translator, fake_messages, monkeypatch
):
    translator = load_translator()
    _install_messages(translator, monkeypatch, fake_messages)

    assert translator.translate("agent.missing.name", "en") == "agent.missing.name"


def test_existing_key_missing_target_lang_returns_zh(
    load_translator, fake_messages, monkeypatch
):
    translator = load_translator()
    _install_messages(translator, monkeypatch, fake_messages)

    assert translator.translate("agent.zh_only.name", "ru") == "仅中文"


def test_translate_or_none_missing_returns_none(
    load_translator, fake_messages, monkeypatch
):
    translator = load_translator()
    _install_messages(translator, monkeypatch, fake_messages)

    assert translator.translate_or_none("agent.missing.name", "en") is None


def test_translate_or_none_present_returns_value(
    load_translator, fake_messages, monkeypatch
):
    translator = load_translator()
    _install_messages(translator, monkeypatch, fake_messages)

    assert translator.translate_or_none("agent.demo.name", "zh") == "演示"

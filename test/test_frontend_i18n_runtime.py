"""前端 i18n 语言运行时静态契约测试。"""

from pathlib import Path
import re
from runpy import run_path

import pytest

from scripts.check_frontend_i18n import extract_named_function


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "scripts/build_global_html.py"
GLOBAL_HTML = PROJECT_ROOT / "src/shuyixiao_agent/static/global.html"


@pytest.fixture(scope="module")
def runtime_block() -> str:
    namespace = run_path(str(BUILD_SCRIPT))
    return namespace["generate_i18n_js"]()


@pytest.fixture(scope="module")
def global_html() -> str:
    return GLOBAL_HTML.read_text(encoding="utf-8")


def _function_block(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    next_function = source.find("\n        function ", start + 1)
    return source[start:] if next_function == -1 else source[start:next_function]


def test_invalid_or_empty_stored_language_initializes_to_english(runtime_block):
    assert (
        "let currentLang = "
        "normalizeFrontendLang(localStorage.getItem('gaia_lang'));"
    ) in runtime_block


def test_normalize_frontend_lang_returns_only_supported_values(runtime_block):
    assert "new Set(['en', 'zh', 'ru'])" in runtime_block
    normalize_block = _function_block(runtime_block, "normalizeFrontendLang")
    assert "SUPPORTED_FRONTEND_LANGS.has(lang) ? lang : 'en'" in normalize_block


def test_t_falls_back_from_current_language_to_en_then_zh_then_key(runtime_block):
    translate_block = _function_block(runtime_block, "t")
    assert "entry[currentLang] || entry.en || entry.zh || key" in translate_block


def test_t_replaces_every_occurrence_of_each_parameter(runtime_block):
    translate_block = _function_block(runtime_block, "t")
    assert "function t(key, params = {})" in translate_block
    assert "Object.entries(params).forEach(([name, rawValue])" in translate_block
    assert "value.split(`{${name}}`).join(String(rawValue))" in translate_block


def test_t_keeps_dollar_ampersand_and_group_values_literal(runtime_block):
    translate_block = _function_block(runtime_block, "t")
    assert ".split(`{${name}}`).join(String(rawValue))" in translate_block
    assert ".replace(" not in translate_block


def test_set_language_persists_normalized_language_and_applies_translations(
    runtime_block,
):
    set_language_block = _function_block(runtime_block, "setLanguage")
    assert "const normalizedLang = normalizeFrontendLang(lang);" in set_language_block
    assert "currentLang = normalizedLang;" in set_language_block
    assert "localStorage.setItem('gaia_lang', normalizedLang);" in set_language_block
    assert set_language_block.count("applyTranslations();") == 1


def test_set_language_dispatches_one_normalized_event(runtime_block):
    set_language_block = _function_block(runtime_block, "setLanguage")
    assert "const previousLang = currentLang;" in set_language_block
    assert set_language_block.count("new CustomEvent('languagechange'") == 1
    assert "detail: { lang: normalizedLang, previousLang }" in set_language_block


def test_apply_translations_handles_text_and_placeholder_separately(runtime_block):
    apply_block = _function_block(runtime_block, "applyTranslations")
    text_selector = "document.querySelectorAll('[data-i18n]')"
    placeholder_selector = "document.querySelectorAll('[data-i18n-placeholder]')"
    text_start = apply_block.index(text_selector)
    placeholder_start = apply_block.index(placeholder_selector)
    placeholder_end = apply_block.find("document.title", placeholder_start)
    placeholder_end = None if placeholder_end == -1 else placeholder_end

    text_updates = apply_block[text_start:placeholder_start]
    placeholder_updates = apply_block[placeholder_start:placeholder_end]
    assert "textContent =" in text_updates
    assert "placeholder =" not in text_updates
    assert "placeholder =" in placeholder_updates
    assert "textContent =" not in placeholder_updates


def test_apply_translations_syncs_language_selector(runtime_block):
    apply_block = _function_block(runtime_block, "applyTranslations")
    assert "document.getElementById('langSelect')" in apply_block
    assert "langSelect.value = currentLang" in apply_block


def test_languagechange_has_one_central_listener(global_html):
    listener_pattern = re.compile(
        r"document\.addEventListener\(\s*['\"]languagechange['\"]\s*,"
        r"\s*\(\)\s*=>\s*\{(?P<body>.*?)\}\s*\);",
        re.DOTALL,
    )
    listeners = list(listener_pattern.finditer(global_html))

    assert len(listeners) == 1
    body = re.sub(r"\s+", " ", listeners[0].group("body")).strip()
    assert body == "void rerenderVisibleLocalizedState();"


def test_rerender_visible_state_uses_stable_order_without_destructive_actions(
    global_html,
):
    block = extract_named_function(global_html, "rerenderVisibleLocalizedState")
    assert block is not None, "JS function not found: rerenderVisibleLocalizedState"

    ordered_calls = (
        "updateLegalTaskSection();",
        "renderLegalAgentSelection();",
        "renderLegalAgentGapWarning();",
        "displayCollaborationResult(currentCollaborationResult",
        "captureKnowledgeSelectValues();",
        "renderKnowledgeBaseGroups(knowledgeBases || []);",
        "updateKnowledgeBaseSelects(knowledgeBases || []);",
        "restoreKnowledgeSelectValues(",
        "await loadCollaborationData(",
    )
    positions = [block.index(call) for call in ordered_calls]
    assert positions == sorted(positions)

    for forbidden in (
        "startCollaboration(",
        "parseLegalContractFile(",
        "resetCollaborationSection(",
        "currentCollaborationResult = null",
        "currentCollaborationSnapshot = null",
        "selectedLegalAgentNames = []",
        "legalTask.value = ''",
        "ragUploadFile.value = ''",
        "legalContractStructureSummary = ''",
    ):
        assert forbidden not in block

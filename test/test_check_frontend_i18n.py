"""前端 I18N 字典完整性检查器测试。"""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "check_frontend_i18n.py"


VALID_I18N = {
    "status.loaded_policies": {
        "en": "Loaded {count} policies.",
        "zh": "已加载 {count} 种策略。",
        "ru": "Загружено политик: {count}.",
    }
}


def _check_i18n_catalog(catalog: dict[str, dict[str, str]]) -> list[str]:
    module = import_module("scripts.check_frontend_i18n")
    return module.check_i18n_catalog(catalog)


def _scan_visible_html(html: str) -> list[str]:
    module = import_module("scripts.check_frontend_i18n")
    return module.scan_visible_html(html)


def _scan_named_js_functions(source: str, names: list[str]) -> list[str]:
    module = import_module("scripts.check_frontend_i18n")
    return module.scan_named_js_functions(source, names)


def test_valid_i18n_catalog_passes():
    assert _check_i18n_catalog(deepcopy(VALID_I18N)) == []


def test_catalog_missing_ru_is_rejected():
    catalog = deepcopy(VALID_I18N)
    del catalog["status.loaded_policies"]["ru"]

    assert _check_i18n_catalog(catalog) == [
        "status.loaded_policies: language mismatch: "
        "expected ['en', 'ru', 'zh'], got ['en', 'zh']"
    ]


def test_catalog_empty_en_is_rejected():
    catalog = deepcopy(VALID_I18N)
    catalog["status.loaded_policies"]["en"] = "   "

    assert _check_i18n_catalog(catalog) == [
        "status.loaded_policies: empty translation for en"
    ]


def test_catalog_invalid_key_is_rejected():
    catalog = {"Status.loaded-policies": deepcopy(VALID_I18N["status.loaded_policies"])}

    assert _check_i18n_catalog(catalog) == [
        "Status.loaded-policies: invalid i18n key"
    ]


def test_placeholder_sets_must_match():
    catalog = deepcopy(VALID_I18N)
    catalog["status.loaded_policies"]["ru"] = "Загружены политики."

    assert _check_i18n_catalog(catalog) == [
        "status.loaded_policies: placeholder mismatch for ru: "
        "expected ['count'], got []"
    ]


def test_placeholder_names_must_match():
    catalog = deepcopy(VALID_I18N)
    catalog["status.loaded_policies"]["ru"] = "Загружено политик: {name}."

    assert _check_i18n_catalog(catalog) == [
        "status.loaded_policies: placeholder mismatch for ru: "
        "expected ['count'], got ['name']"
    ]


@pytest.mark.parametrize("fragment", ["<script", "javascript:", "onerror=", "onload="])
def test_dangerous_translation_fragment_is_rejected(fragment: str):
    catalog = deepcopy(VALID_I18N)
    catalog["status.loaded_policies"]["en"] = f"Unsafe {fragment} {{count}} value"

    assert _check_i18n_catalog(catalog) == [
        f"status.loaded_policies: dangerous fragment {fragment!r} for en"
    ]


def test_catalog_allows_plain_angle_brackets_in_legal_text():
    catalog = deepcopy(VALID_I18N)
    catalog["status.loaded_policies"]["en"] = (
        "Damages in {count} cases may be < or > the stated cap."
    )

    assert _check_i18n_catalog(catalog) == []


def test_nested_visible_html_text_without_i18n_marker_is_rejected():
    html = (
        '<div id="multiagentTab"><section><span>中文未标注</span></section></div>'
    )

    assert _scan_visible_html(html) == [
        "HTML text contains Chinese without data-i18n: 中文未标注"
    ]


def test_visible_html_text_with_i18n_marker_passes():
    html = '<div class="tabs"><button data-i18n="tab_multiagent">多智能体</button></div>'

    assert _scan_visible_html(html) == []


@pytest.mark.parametrize(
    ("attribute", "marker"),
    [
        ("placeholder", "data-i18n-placeholder"),
        ("title", "data-i18n-title"),
        ("aria-label", "data-i18n-aria-label"),
    ],
)
def test_visible_html_attribute_without_i18n_marker_is_rejected(
    attribute: str, marker: str
):
    html = f'<div id="knowledgeTab"><input {attribute}="中文属性"></div>'

    assert _scan_visible_html(html) == [
        f"HTML attribute {attribute} contains Chinese without {marker}: 中文属性"
    ]


def test_html_comments_are_ignored():
    html = '<div id="knowledgeTab"><!-- 中文注释 --><span data-i18n="ok">中文</span></div>'

    assert _scan_visible_html(html) == []


def test_dev_only_html_is_out_of_scope():
    html = '<div class="tabs"><div class="dev-only">中文保留</div></div>'

    assert _scan_visible_html(html) == []


def test_named_js_function_with_chinese_string_is_rejected():
    source = 'function target() { alert("中文状态"); }'

    assert _scan_named_js_functions(source, ["target"]) == [
        "JS function target contains Chinese string: 中文状态"
    ]


def test_named_js_function_using_translation_key_passes():
    source = "function target() { return t('status.ready'); }"

    assert _scan_named_js_functions(source, ["target"]) == []


def test_js_line_and_block_comments_are_ignored():
    source = """
    function target() {
        // 中文行注释 }
        /* 中文块注释 { } */
        return t('status.ready');
    }
    """

    assert _scan_named_js_functions(source, ["target"]) == []


def test_js_i18n_zh_values_outside_named_function_are_ignored():
    source = """
    const I18N = { ready: { zh: '中文保留' } };
    function target() { return t('ready'); }
    """

    assert _scan_named_js_functions(source, ["target"]) == []


def test_js_dev_only_function_is_out_of_scope():
    source = """
    function devOnly() { alert('中文保留'); }
    function target() { return t('ready'); }
    """

    assert _scan_named_js_functions(source, ["target"]) == []


def test_named_js_function_with_fixed_chinese_template_text_is_rejected():
    source = "function target(userValue) { return `状态：${userValue}`; }"

    assert _scan_named_js_functions(source, ["target"]) == [
        "JS function target contains Chinese template text: 状态："
    ]


def test_named_js_function_with_interpolation_only_template_passes():
    source = "function target(userValue) { return `${userValue}`; }"

    assert _scan_named_js_functions(source, ["target"]) == []


def test_named_js_function_scan_ignores_braces_in_strings_and_comments():
    source = """
    function target() {
        const closingBrace = "}";
        /* } */
        // }
        return "中文状态";
    }
    """

    assert _scan_named_js_functions(source, ["target"]) == [
        "JS function target contains Chinese string: 中文状态"
    ]


def test_named_js_function_isolated_from_unrelated_prior_regex_literal():
    source = """
    const quotePattern = /["']/;
    function target() { return "中文状态"; }
    """

    assert _scan_named_js_functions(source, ["target"]) == [
        "JS function target contains Chinese string: 中文状态"
    ]


def test_missing_named_function_is_an_error():
    assert _scan_named_js_functions("function present() {}", ["missing"]) == [
        "JS function not found: missing"
    ]


def test_cli_returns_zero_for_clean_files_and_one_for_errors(tmp_path: Path):
    build_script = tmp_path / "build_fixture.py"
    build_script.write_text(f"I18N = {VALID_I18N!r}\n", encoding="utf-8")
    clean_html = tmp_path / "clean.html"
    clean_html.write_text(
        """
        <div class="tabs"><button data-i18n="tab_multiagent">中文</button></div>
        <script>function target() { return t('tab_multiagent'); }</script>
        """,
        encoding="utf-8",
    )
    bad_html = tmp_path / "bad.html"
    bad_html.write_text(
        '<div id="multiagentTab"><span>中文残留</span></div>'
        '<script>function target() { return "中文状态"; }</script>',
        encoding="utf-8",
    )

    def run_cli(html_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--build-script",
                str(build_script),
                "--html",
                str(html_path),
                "--function",
                "target",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    clean_result = run_cli(clean_html)
    bad_result = run_cli(bad_html)

    assert clean_result.returncode == 0, clean_result.stderr
    assert bad_result.returncode == 1
    assert f"{bad_html}:1:" in bad_result.stderr
    assert "scope=HTML-visible" in bad_result.stderr
    assert "scope=JS:target" in bad_result.stderr

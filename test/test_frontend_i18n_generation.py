"""国际版前端受控替换、生成一致性与最终收口契约测试。"""

import ast
from html.parser import HTMLParser
from pathlib import Path
import re
from runpy import run_path
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "scripts/build_global_html.py"
STATIC_DIR = PROJECT_ROOT / "src/shuyixiao_agent/static"
INDEX_HTML = STATIC_DIR / "index.html"
GLOBAL_HTML = STATIC_DIR / "global.html"
CHECK_SCRIPT = PROJECT_ROOT / "scripts/check_frontend_i18n.py"


class _DomContractParser(HTMLParser):
    """提取生成前后必须保持稳定的业务 DOM 契约。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.data_tabs: set[str] = set()
        self.handlers: set[tuple[str, str]] = set()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id") or ""
        # global.html 唯一允许新增的 ID 是国际版语言选择器。
        if element_id != "langSelect":
            if element_id:
                self.ids.add(element_id)
            for name, value in attrs:
                if name.startswith("on") and value is not None:
                    called_functions = re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", value)
                    self.handlers.update((name, function) for function in called_functions)
        if attributes.get("data-tab"):
            self.data_tabs.add(attributes["data-tab"])


def _dom_contract(source: str) -> _DomContractParser:
    parser = _DomContractParser()
    parser.feed(source)
    parser.close()
    return parser


@pytest.fixture()
def build_namespace() -> dict:
    return run_path(str(BUILD_SCRIPT))


def test_replace_once_replaces_single_match(build_namespace):
    replace_once = build_namespace["replace_once"]

    assert replace_once("before x after", "x", "y", "demo") == "before y after"


@pytest.mark.parametrize("content,count", [("none", 0), ("x x", 2)])
def test_replace_once_rejects_non_unique_match(build_namespace, content, count):
    build_rule_error = build_namespace["BuildRuleError"]
    replace_once = build_namespace["replace_once"]

    with pytest.raises(build_rule_error, match=rf"demo.*{count}"):
        replace_once(content, "x", "y", "demo")


def test_build_failure_does_not_overwrite_existing_output(
    build_namespace,
    tmp_path,
):
    index_path = tmp_path / "index.html"
    output_path = tmp_path / "global.html"
    index_path.write_text("<html>source</html>", encoding="utf-8")
    output_path.write_text("existing output", encoding="utf-8")

    def fail_render(_index_content: str) -> str:
        raise RuntimeError("render failed")

    build_global_html = build_namespace["build_global_html"]
    build_global_html.__globals__.update(
        INDEX_PATH=str(index_path),
        OUTPUT_PATH=str(output_path),
        render_global_html=fail_render,
    )

    with pytest.raises(RuntimeError, match="render failed"):
        build_global_html()

    assert output_path.read_text(encoding="utf-8") == "existing output"


def test_render_global_html_is_deterministic(build_namespace):
    index_source = INDEX_HTML.read_text(encoding="utf-8")
    render_global_html = build_namespace["render_global_html"]

    first = render_global_html(index_source)
    second = render_global_html(index_source)

    assert first == second


def test_generated_output_matches_committed_global_html(build_namespace, tmp_path):
    generated_path = tmp_path / "global.html"
    build_global_html = build_namespace["build_global_html"]
    build_global_html.__globals__["OUTPUT_PATH"] = str(generated_path)

    build_global_html()

    assert generated_path.read_text(encoding="utf-8") == GLOBAL_HTML.read_text(
        encoding="utf-8"
    )


def test_domestic_index_excludes_global_language_runtime():
    index_source = INDEX_HTML.read_text(encoding="utf-8")

    assert "const I18N" not in index_source
    assert "langSelect" not in index_source
    assert "setLanguage" not in index_source


def test_generated_html_preserves_business_dom_and_handler_contracts():
    index_contract = _dom_contract(INDEX_HTML.read_text(encoding="utf-8"))
    global_contract = _dom_contract(GLOBAL_HTML.read_text(encoding="utf-8"))

    assert global_contract.ids == index_contract.ids
    assert global_contract.data_tabs == index_contract.data_tabs
    assert global_contract.handlers == index_contract.handlers


def test_real_frontend_i18n_checker_exits_zero():
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_i18n_catalog_literals_have_no_duplicate_python_keys():
    tree = ast.parse(BUILD_SCRIPT.read_text(encoding="utf-8"))
    duplicate_errors: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        catalog_names = [
            target.id
            for target in node.targets
            if isinstance(target, ast.Name)
            and (target.id == "I18N" or target.id.endswith("_I18N"))
        ]
        if not catalog_names:
            continue

        seen: dict[str, int] = {}
        for key_node in node.value.keys:
            if not (
                isinstance(key_node, ast.Constant)
                and isinstance(key_node.value, str)
            ):
                continue
            key = key_node.value
            if key in seen:
                duplicate_errors.append(
                    f"{catalog_names[0]}: duplicate key {key!r} "
                    f"at lines {seen[key]} and {key_node.lineno}"
                )
            else:
                seen[key] = key_node.lineno

    assert duplicate_errors == []

"""前端 apiFetch 语言 Header 静态与生成一致性测试。"""

from pathlib import Path
from runpy import run_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "src/shuyixiao_agent/static"
INDEX_HTML = STATIC_DIR / "index.html"
GLOBAL_HTML = STATIC_DIR / "global.html"
BUILD_SCRIPT = PROJECT_ROOT / "scripts/build_global_html.py"

DOMESTIC_LANG_HEADER_SNIPPET = """            const lang = localStorage.getItem('gaia_lang');
            if (lang) {
                headers.set('X-User-Lang', lang);
            }"""

GLOBAL_LANG_HEADER_SNIPPET = """            const lang = normalizeFrontendLang(localStorage.getItem('gaia_lang'));
            headers.set('X-User-Lang', lang);"""


def _api_fetch_block(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    start = content.index("async function apiFetch")
    end = content.index("window.fetch = apiFetch", start)
    return content[start:end]


def test_global_html_apifetch_injects_x_user_lang():
    assert GLOBAL_LANG_HEADER_SNIPPET in _api_fetch_block(GLOBAL_HTML)


def test_index_html_apifetch_conditional_inject():
    assert DOMESTIC_LANG_HEADER_SNIPPET in _api_fetch_block(INDEX_HTML)


def test_build_global_html_output_consistent(tmp_path):
    namespace = run_path(str(BUILD_SCRIPT))
    build_global_html = namespace["build_global_html"]
    generated_path = tmp_path / "global.html"
    build_global_html.__globals__["OUTPUT_PATH"] = str(generated_path)

    build_global_html()

    assert generated_path.read_text(encoding="utf-8") == GLOBAL_HTML.read_text(
        encoding="utf-8"
    )

#!/usr/bin/env python3
"""前端 I18N 翻译字典的纯函数检查核心。"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import runpy
import sys
from typing import Mapping


SUPPORTED_LANGS = ("en", "zh", "ru")
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*$")
PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
DANGEROUS_FRAGMENTS = ("<script", "javascript:", "onerror=", "onload=")
CHINESE_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
VISIBLE_ATTRIBUTES = {
    "placeholder": "data-i18n-placeholder",
    "title": "data-i18n-title",
    "aria-label": "data-i18n-aria-label",
}
VISIBLE_SCOPE_IDS = {"langSelect", "multiagentTab", "knowledgeTab"}
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_global_html.py"
DEFAULT_HTML = PROJECT_ROOT / "src" / "shuyixiao_agent" / "static" / "global.html"
DEFAULT_JS_FUNCTIONS = (
    "t",
    "setLanguage",
    "applyTranslations",
    "apiFetch",
    "handleUnauthorizedSession",
    "logoutCurrentUser",
    "rerenderVisibleLocalizedState",
    "createKnowledgeBase",
    "createUserKnowledgeBase",
    "createPublicKnowledgeBase",
    "uploadTexts",
    "renderRagFileUploadSuccess",
    "uploadFile",
    "getKnowledgeInfo",
    "loadMappings",
    "loadUploadAudit",
    "clearKnowledgeBase",
    "deleteKnowledgeBaseCollection",
    "resetDeletedKnowledgeBaseSelections",
    "syncKnowledgeBaseSelection",
    "loadDocuments",
    "refreshDocuments",
    "viewDocument",
    "closeDocModal",
    "deleteCurrentDoc",
    "deleteDocumentById",
    "getKnowledgeBaseScopeLabel",
    "formatKnowledgeBaseLabel",
    "renderKnowledgeBaseGroups",
    "loadAllCollections",
    "updateKnowledgeBaseSelects",
    "selectKnowledgeBase",
    "toggleDocSelection",
    "updateBatchDeleteButton",
    "batchDeleteDocuments",
    "loadCollaborationData",
    "updateTeamInfo",
    "syncLegalSelectionPolicy",
    "updateLegalTaskSection",
    "applyLegalTaskTemplate",
    "initializeLegalAgentSelection",
    "enforceRequiredLegalAgents",
    "renderLegalAgentSelection",
    "renderLegalAgentGapWarning",
    "toggleLegalAgent",
    "restoreLegalAgentDefaults",
    "parseLegalContractFile",
    "parseLegalContractFileFromPath",
    "applyParsedContractResult",
    "renderParsedContractStatus",
    "formatContractStructureSummary",
    "renderContractSummarySection",
    "buildCollaborationSnapshot",
    "readSafeStreamError",
    "handleSSEEventBlock",
    "startCollaboration",
    "handleCollaborationEvent",
    "displayCollaborationResult",
    "resetCollaborationSection",
    "toggleCollaborationSection",
    "displayAgentContributions",
    "displayCollaborationMessages",
    "clearCollaborationResult",
    "copyCollaborationResult",
    "downloadCollaborationResult",
    "showTeamDetails",
    "showModeDetails",
    "showCollaborationDetails",
)


def extract_placeholders(value: str) -> set[str]:
    """提取翻译值中的命名占位符集合。"""
    return set(PLACEHOLDER_PATTERN.findall(value))


def check_i18n_catalog(
    catalog: Mapping[str, Mapping[str, str]],
) -> list[str]:
    """按稳定顺序返回前端翻译字典的全部错误。"""
    errors: list[str] = []
    expected_langs = sorted(SUPPORTED_LANGS)

    for key in sorted(catalog):
        translations = catalog[key]

        if not KEY_PATTERN.fullmatch(key):
            errors.append(f"{key}: invalid i18n key")

        actual_langs = sorted(translations)
        if actual_langs != expected_langs:
            errors.append(
                f"{key}: language mismatch: expected {expected_langs}, "
                f"got {actual_langs}"
            )

        valid_values: dict[str, str] = {}
        for lang in SUPPORTED_LANGS:
            if lang not in translations:
                continue
            value = translations[lang]
            if not isinstance(value, str):
                errors.append(
                    f"{key}: non-string translation for {lang}: "
                    f"got {type(value).__name__}"
                )
                continue
            if not value.strip():
                errors.append(f"{key}: empty translation for {lang}")
                continue
            valid_values[lang] = value

        reference_lang = next(
            (lang for lang in SUPPORTED_LANGS if lang in valid_values), None
        )
        if reference_lang is not None:
            expected_placeholders = extract_placeholders(valid_values[reference_lang])
            for lang in SUPPORTED_LANGS:
                if lang == reference_lang or lang not in valid_values:
                    continue
                actual_placeholders = extract_placeholders(valid_values[lang])
                if actual_placeholders != expected_placeholders:
                    errors.append(
                        f"{key}: placeholder mismatch for {lang}: "
                        f"expected {sorted(expected_placeholders)}, "
                        f"got {sorted(actual_placeholders)}"
                    )

        for lang in SUPPORTED_LANGS:
            value = valid_values.get(lang)
            if value is None:
                continue
            lowered_value = value.lower()
            for fragment in DANGEROUS_FRAGMENTS:
                if fragment in lowered_value:
                    errors.append(
                        f"{key}: dangerous fragment {fragment!r} for {lang}"
                    )

    return errors


class _VisibleHTMLScanner(HTMLParser):
    """只扫描 P1b 可见 DOM scope 的中文文本和属性。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []
        self.stack: list[tuple[str, dict[str, str | None], bool, bool]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        parent_scope = self.stack[-1][2] if self.stack else False
        parent_dev_only = self.stack[-1][3] if self.stack else False
        in_scope = (
            parent_scope
            or attributes.get("id") in VISIBLE_SCOPE_IDS
            or "tabs" in classes
        )
        dev_only = parent_dev_only or "dev-only" in classes

        if in_scope and not dev_only:
            for attribute, marker in VISIBLE_ATTRIBUTES.items():
                value = attributes.get(attribute)
                if value and CHINESE_PATTERN.search(value) and marker not in attributes:
                    self.errors.append(
                        f"HTML attribute {attribute} contains Chinese without "
                        f"{marker}: {value.strip()}"
                    )

        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, attributes, in_scope, dev_only))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if not self.stack or not CHINESE_PATTERN.search(data):
            return
        _, attributes, in_scope, dev_only = self.stack[-1]
        if in_scope and not dev_only and "data-i18n" not in attributes:
            self.errors.append(
                f"HTML text contains Chinese without data-i18n: {data.strip()}"
            )


def scan_visible_html(html: str) -> list[str]:
    """返回 P1b 可见 DOM 中未标注的固定中文。"""
    scanner = _VisibleHTMLScanner()
    scanner.feed(html)
    scanner.close()
    return scanner.errors


def _mask_js_non_code(source: str) -> str:
    """保留 JS 代码和换行，屏蔽字符串、模板字面量及注释。"""
    masked = list(source)
    index = 0
    state = "code"
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""

        if state == "code":
            if char in "'\"`":
                state = {"'": "single", '"': "double", "`": "template"}[char]
                masked[index] = " "
            elif char == "/" and following == "/":
                state = "line_comment"
                masked[index] = masked[index + 1] = " "
                index += 1
            elif char == "/" and following == "*":
                state = "block_comment"
                masked[index] = masked[index + 1] = " "
                index += 1
        elif state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                masked[index] = " "
        elif state == "block_comment":
            if char == "*" and following == "/":
                masked[index] = masked[index + 1] = " "
                index += 1
                state = "code"
            elif char != "\n":
                masked[index] = " "
        else:
            masked[index] = " " if char != "\n" else "\n"
            if char == "\\" and following:
                masked[index + 1] = " " if following != "\n" else "\n"
                index += 1
            elif (state == "single" and char == "'") or (
                state == "double" and char == '"'
            ) or (state == "template" and char == "`"):
                state = "code"
        index += 1
    return "".join(masked)


def extract_named_function(source: str, name: str) -> str | None:
    """提取具名 function 声明，忽略字符串、模板和注释内的花括号。"""
    pattern = re.compile(
        rf"\b(?:async\s+)?function\s+{re.escape(name)}\s*\("
    )
    source_match = pattern.search(source)
    if source_match is None:
        return None

    candidate = source[source_match.start() :]
    masked = _mask_js_non_code(candidate)
    match = pattern.match(masked)
    if match is None:
        return None

    opening_parenthesis = match.end() - 1
    parenthesis_depth = 0
    body_start = None
    for index in range(opening_parenthesis, len(masked)):
        char = masked[index]
        if char == "(":
            parenthesis_depth += 1
        elif char == ")":
            parenthesis_depth -= 1
            if parenthesis_depth == 0:
                body_start = masked.find("{", index + 1)
                break
    if body_start is None or body_start < 0:
        return None

    brace_depth = 0
    for index in range(body_start, len(masked)):
        char = masked[index]
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth == 0:
                return candidate[match.start() : index + 1]
    return None


def _read_quoted(source: str, start: int, quote: str) -> tuple[str, int]:
    index = start + 1
    content: list[str] = []
    while index < len(source):
        char = source[index]
        if char == "\\" and index + 1 < len(source):
            content.extend((char, source[index + 1]))
            index += 2
            continue
        if char == quote:
            return "".join(content), index + 1
        content.append(char)
        index += 1
    return "".join(content), index


def _skip_template_expression(source: str, start: int) -> int:
    depth = 1
    index = start
    while index < len(source) and depth:
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if char in "'\"`":
            _, index = _read_quoted(source, index, char)
            continue
        if char == "/" and following == "/":
            newline = source.find("\n", index + 2)
            index = len(source) if newline < 0 else newline + 1
            continue
        if char == "/" and following == "*":
            ending = source.find("*/", index + 2)
            index = len(source) if ending < 0 else ending + 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return index


def _read_template(source: str, start: int) -> tuple[list[str], int]:
    index = start + 1
    chunks: list[str] = []
    current: list[str] = []
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if char == "\\" and following:
            current.extend((char, following))
            index += 2
            continue
        if char == "`":
            chunks.append("".join(current))
            return chunks, index + 1
        if char == "$" and following == "{":
            chunks.append("".join(current))
            current = []
            index = _skip_template_expression(source, index + 2)
            continue
        current.append(char)
        index += 1
    chunks.append("".join(current))
    return chunks, index


def _scan_js_literals(function_source: str, name: str) -> list[str]:
    errors: list[str] = []
    index = 0
    while index < len(function_source):
        char = function_source[index]
        following = (
            function_source[index + 1] if index + 1 < len(function_source) else ""
        )
        if char == "/" and following == "/":
            newline = function_source.find("\n", index + 2)
            index = len(function_source) if newline < 0 else newline + 1
            continue
        if char == "/" and following == "*":
            ending = function_source.find("*/", index + 2)
            index = len(function_source) if ending < 0 else ending + 2
            continue
        if char in "'\"":
            value, index = _read_quoted(function_source, index, char)
            if CHINESE_PATTERN.search(value):
                errors.append(
                    f"JS function {name} contains Chinese string: {value.strip()}"
                )
            continue
        if char == "`":
            chunks, index = _read_template(function_source, index)
            for chunk in chunks:
                if CHINESE_PATTERN.search(chunk):
                    errors.append(
                        f"JS function {name} contains Chinese template text: "
                        f"{chunk.strip()}"
                    )
            continue
        index += 1
    return errors


def scan_named_js_functions(source: str, names: list[str] | tuple[str, ...]) -> list[str]:
    """扫描显式具名 JS 函数中的固定中文字面量。"""
    errors: list[str] = []
    for name in names:
        function_source = extract_named_function(source, name)
        if function_source is None:
            errors.append(f"JS function not found: {name}")
            continue
        errors.extend(_scan_js_literals(function_source, name))
    return errors


def _line_number(source: str, position: int) -> int:
    return 1 if position < 0 else source.count("\n", 0, position) + 1


def _print_diagnostic(
    path: Path, source: str, scope: str, error: str, start: int = 0
) -> int:
    detail = error.rsplit(": ", 1)[-1]
    position = source.find(detail, start)
    line = _line_number(source, position)
    rendered_error = " ".join(error.split())
    print(f"{path}:{line}: [scope={scope}] {rendered_error}", file=sys.stderr)
    return start if position < 0 else position + len(detail)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-script", type=Path, default=DEFAULT_BUILD_SCRIPT)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--function", action="append", dest="functions")
    args = parser.parse_args(argv)

    build_source = args.build_script.read_text(encoding="utf-8")
    html = args.html.read_text(encoding="utf-8")
    namespace = runpy.run_path(str(args.build_script))
    catalog = namespace["I18N"]
    functions = tuple(args.functions or DEFAULT_JS_FUNCTIONS)

    catalog_errors = check_i18n_catalog(catalog)
    html_errors = scan_visible_html(html)
    js_errors = scan_named_js_functions(html, functions)

    for error in catalog_errors:
        key = error.split(":", 1)[0]
        key_position = build_source.find(repr(key))
        line = _line_number(build_source, key_position)
        print(
            f"{args.build_script}:{line}: [scope=I18N] {' '.join(error.split())}",
            file=sys.stderr,
        )
    html_cursor = 0
    for error in html_errors:
        html_cursor = _print_diagnostic(
            args.html, html, "HTML-visible", error, html_cursor
        )
    js_cursors: dict[str, int] = {}
    for error in js_errors:
        match = re.match(r"JS function (?:not found: )?([^ ]+)", error)
        function_name = match.group(1) if match else "unknown"
        function_start = js_cursors.get(function_name)
        if function_start is None:
            declaration = re.search(
                rf"\b(?:async\s+)?function\s+{re.escape(function_name)}\s*\(",
                html,
            )
            function_start = declaration.start() if declaration else 0
        js_cursors[function_name] = _print_diagnostic(
            args.html, html, f"JS:{function_name}", error, function_start
        )

    errors = catalog_errors + html_errors + js_errors
    if errors:
        return 1
    print("frontend i18n check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

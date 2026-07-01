#!/usr/bin/env python3
"""检查后端 i18n 翻译表的完整性。"""

from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path
import re
import sys
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

DEFAULT_MODULE = "shuyixiao_agent.i18n.messages"
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
PLACEHOLDERS = ("TODO", "待翻译", "???")


def check_messages(
    messages: Mapping[str, Mapping[str, str]], supported_langs: tuple[str, ...]
) -> list[str]:
    """返回翻译表中的全部校验错误。"""
    errors: list[str] = []
    for key, translations in messages.items():
        if not KEY_PATTERN.fullmatch(key):
            errors.append(f"Invalid key naming: {key}")

        for lang in supported_langs:
            if lang not in translations:
                errors.append(f"Missing language '{lang}' for key '{key}'")
                continue

            value = translations[lang]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Empty value for key '{key}', language '{lang}'")
                continue

            for placeholder in PLACEHOLDERS:
                if placeholder in value:
                    errors.append(
                        f"Placeholder '{placeholder}' in key '{key}', language '{lang}'"
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", default=DEFAULT_MODULE, help="翻译表模块导入路径")
    args = parser.parse_args()

    module = import_module(args.module)
    errors = check_messages(module.MESSAGES, tuple(module.SUPPORTED_LANGS))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"i18n completeness check passed: {len(module.MESSAGES)} keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

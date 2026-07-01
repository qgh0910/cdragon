"""i18n 翻译表完整性检查脚本测试。"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from textwrap import dedent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "check_i18n_completeness.py"


def _write_messages_module(tmp_path: Path, messages: str) -> str:
    module_path = tmp_path / "fixture_messages.py"
    module_path.write_text(
        dedent(
            f'''\
            SUPPORTED_LANGS = ("en", "zh", "ru")
            MESSAGES = {messages}
            '''
        ),
        encoding="utf-8",
    )
    return module_path.stem


def _run_check(module: str | None = None, extra_pythonpath: Path | None = None):
    command = [sys.executable, str(SCRIPT_PATH)]
    if module:
        command.extend(["--module", module])

    env = os.environ.copy()
    python_paths = [str(PROJECT_ROOT / "src")]
    if extra_pythonpath:
        python_paths.insert(0, str(extra_pythonpath))
    if env.get("PYTHONPATH"):
        python_paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_paths)

    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_complete_messages_returns_exit_0(tmp_path):
    module = _write_messages_module(
        tmp_path,
        '{"agent.demo.name": {"en": "Demo", "zh": "演示", "ru": "Демо"}}',
    )

    result = _run_check(module, tmp_path)

    assert result.returncode == 0, result.stderr


def test_missing_lang_returns_exit_1(tmp_path):
    module = _write_messages_module(
        tmp_path,
        '{"agent.demo.name": {"en": "Demo", "zh": "演示"}}',
    )

    result = _run_check(module, tmp_path)

    assert result.returncode == 1
    assert "agent.demo.name" in result.stderr
    assert "ru" in result.stderr


def test_bad_key_naming_returns_exit_1(tmp_path):
    module = _write_messages_module(
        tmp_path,
        '{"Agent.demo.name": {"en": "Demo", "zh": "演示", "ru": "Демо"}}',
    )

    result = _run_check(module, tmp_path)

    assert result.returncode == 1
    assert "Agent.demo.name" in result.stderr


def test_empty_value_returns_exit_1(tmp_path):
    module = _write_messages_module(
        tmp_path,
        '{"agent.demo.name": {"en": "", "zh": "演示", "ru": "Демо"}}',
    )

    result = _run_check(module, tmp_path)

    assert result.returncode == 1
    assert "agent.demo.name" in result.stderr
    assert "en" in result.stderr


def test_placeholder_value_returns_exit_1(tmp_path):
    module = _write_messages_module(
        tmp_path,
        '{"agent.demo.name": {"en": "TODO", "zh": "待翻译", "ru": "???"}}',
    )

    result = _run_check(module, tmp_path)

    assert result.returncode == 1
    assert "agent.demo.name" in result.stderr
    assert "TODO" in result.stderr
    assert "待翻译" in result.stderr
    assert "???" in result.stderr


def test_real_messages_pass():
    result = _run_check()

    assert result.returncode == 0, result.stderr

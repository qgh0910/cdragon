"""LPOS 合同解析配置与安全审计测试。"""

import json
from pathlib import Path

from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.config import settings
from src.shuyixiao_agent.lpos import audit


def _insert_test_user(db_path, user_id="usr_owner"):
    """插入固定 ID 用户，满足 audit_log 的 actor 外键。"""
    storage.initialize_auth_storage(db_path)
    with storage.open_auth_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO users (
                id, username, display_name, password_salt, password_hash,
                password_iterations, role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, user_id, "审计测试用户", "salt", "hash", 310000, "user"),
        )
        connection.commit()


def test_lpos_contract_parse_config_defaults_exist():
    assert settings.lpos_contract_parse_max_chars == 200000
    assert settings.lpos_contract_parse_max_clauses == 300
    assert settings.lpos_contract_parse_clause_preview_chars == 1200
    assert settings.lpos_contract_parse_source_preview_chars == 160
    assert settings.lpos_contract_parse_use_llm is False
    assert settings.lpos_contract_parse_llm_timeout == 60


def test_env_example_documents_lpos_contract_parse_settings():
    env_example = (Path(__file__).parents[1] / ".env.example").read_text(encoding="utf-8")

    assert "LPOS_CONTRACT_PARSE_MAX_CHARS=200000" in env_example
    assert "LPOS_CONTRACT_PARSE_MAX_CLAUSES=300" in env_example
    assert "LPOS_CONTRACT_PARSE_CLAUSE_PREVIEW_CHARS=1200" in env_example
    assert "LPOS_CONTRACT_PARSE_SOURCE_PREVIEW_CHARS=160" in env_example
    assert "LPOS_CONTRACT_PARSE_USE_LLM=false" in env_example
    assert "LPOS_CONTRACT_PARSE_LLM_TIMEOUT=60" in env_example


def test_lpos_audit_log_filters_contract_body(tmp_path, monkeypatch):
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    _insert_test_user(db_path)

    audit.record_contract_event(
        event="contract_parse_success",
        user_id="usr_owner",
        tenant_id="default",
        file_id="20260616_120000_abcdef123456",
        original_filename="contract.txt",
        structure_status="success",
        text_char_count=10000,
        clause_count=5,
        duration_ms=123,
        detail={
            "contract_text": "秘密合同全文",
            "contract_structure": {"clauses": [{"content": "完整条款正文"}]},
            "file_path": "/private/contracts/contract.txt",
            "safe": "ok",
        },
    )

    with storage.open_auth_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM audit_log WHERE action = ?",
            ("contract_parse_success",),
        ).fetchone()

    detail = json.loads(row["detail_json"])
    assert row["actor_user_id"] == "usr_owner"
    assert row["resource_id"] == "20260616_120000_abcdef123456"
    assert row["status"] == "success"
    assert "秘密合同全文" not in row["detail_json"]
    assert "完整条款正文" not in row["detail_json"]
    assert "/private/contracts" not in row["detail_json"]
    assert "contract_text" not in detail
    assert "contract_structure" not in detail
    assert "file_path" not in detail
    assert detail["text_char_count"] == 10000
    assert detail["safe"] == "ok"

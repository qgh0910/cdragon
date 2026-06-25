"""LPOS 合同事件安全审计。"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..auth import storage


SAFE_DETAIL_KEYS = {
    "safe",
    "admin_user_id",
    "target_owner_user_id",
    "parse_after_upload",
    "document_count",
    "file_size",
    "content_type",
}
FAILED_EVENTS = {
    "contract_parse_failed",
    "contract_parse_forbidden",
}


def record_contract_event(
    *,
    event: str,
    user_id: str | None,
    tenant_id: str,
    file_id: str | None = None,
    original_filename: str | None = None,
    structure_status: str | None = None,
    text_char_count: int | None = None,
    clause_count: int | None = None,
    duration_ms: int | None = None,
    error_code: str | None = None,
    error_message_brief: str | None = None,
    detail: dict[str, Any] | None = None,
    status: str | None = None,
    ip_address: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """写入合同审计事件，仅保留摘要级安全字段。"""
    resolved_status = status or ("failed" if event in FAILED_EVENTS else "success")
    if resolved_status not in {"success", "failed"}:
        raise ValueError("合同审计 status 只允许 success 或 failed")

    safe_detail = {
        key: value
        for key, value in (detail or {}).items()
        if key in SAFE_DETAIL_KEYS and _is_json_safe(value)
    }
    _set_if_not_none(safe_detail, "original_filename", _safe_filename(original_filename))
    _set_if_not_none(safe_detail, "structure_status", structure_status)
    _set_if_not_none(safe_detail, "text_char_count", text_char_count)
    _set_if_not_none(safe_detail, "clause_count", clause_count)
    _set_if_not_none(safe_detail, "duration_ms", duration_ms)
    _set_if_not_none(safe_detail, "error_code", error_code)
    _set_if_not_none(
        safe_detail,
        "error_message_brief",
        _sanitize_error_message(error_message_brief),
    )

    storage.initialize_auth_storage(db_path)
    with storage.open_auth_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO audit_log (
                id, actor_user_id, action, resource_type, resource_id,
                scope, status, detail_json, ip_address, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"aud_{uuid.uuid4().hex}",
                user_id,
                event,
                "lpos_contract",
                file_id,
                tenant_id,
                resolved_status,
                json.dumps(safe_detail, ensure_ascii=False),
                ip_address,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        connection.commit()


def _set_if_not_none(target: dict[str, Any], key: str, value: Any) -> None:
    """仅记录存在的审计摘要字段。"""
    if value is not None:
        target[key] = value


def _safe_filename(filename: str | None) -> str | None:
    """原始文件名只保留 basename，避免路径进入审计。"""
    if not filename:
        return None
    return Path(filename).name[:255]


def _sanitize_error_message(message: str | None) -> str | None:
    """过滤错误信息中的绝对路径并限制长度。"""
    if not message:
        return None
    without_windows_paths = re.sub(r"[A-Za-z]:\\[^\s,;]+", "[path]", message)
    without_absolute_paths = re.sub(r"/(?:[^\s,;]+/?)+", "[path]", without_windows_paths)
    return without_absolute_paths[:240]


def _is_json_safe(value: Any) -> bool:
    """限制 detail 白名单值为简单 JSON 数据。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_safe(item) for key, item in value.items())
    return False

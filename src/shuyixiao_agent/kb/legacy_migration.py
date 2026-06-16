"""旧 Chroma collection 迁移报告生成工具。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from ..config import PROJECT_ROOT, settings


DEFAULT_REPORT_PATH = PROJECT_ROOT / "my_docs" / "2026-06-10-legacy-kb-migration-report.md"
DEFAULT_MAPPING_FILE = PROJECT_ROOT / "knowledge_base_mappings.json"
DEFAULT_RECOMMENDED_TARGET = "legacy_admin_only"
RESERVED_NEW_SCOPE_PREFIXES = {"public", "user"}


def build_legacy_migration_rows(
    *,
    client: Any | None = None,
    vector_db_path: str | Path | None = None,
    collection_name_mapping: Mapping[str, str] | None = None,
    mapping_file: str | Path | None = DEFAULT_MAPPING_FILE,
) -> list[dict[str, Any]]:
    """只读扫描 Chroma collections，生成迁移报告行。"""
    chroma_client = client or _create_chroma_client(vector_db_path)
    mappings = _load_mapping_file(mapping_file)
    if collection_name_mapping:
        mappings.update(collection_name_mapping)

    rows: list[dict[str, Any]] = []
    for collection in chroma_client.list_collections():
        collection_name = _collection_name(collection)
        metadata = _collection_metadata(collection)
        original_name = (
            metadata.get("original_name")
            or _resolve_original_name_from_mapping(collection_name, mappings)
            or collection_name
        )
        inferred_tenant = _infer_legacy_tenant(original_name)
        rows.append(
            {
                "collection_name": collection_name,
                "original_name": original_name,
                "inferred_legacy_tenant": inferred_tenant,
                "document_count": _collection_document_count(collection),
                "recommended_target": DEFAULT_RECOMMENDED_TARGET,
                "notes": _build_notes(original_name, inferred_tenant),
            }
        )

    return sorted(rows, key=lambda row: row["collection_name"])


def generate_legacy_migration_report(
    *,
    output_path: str | Path = DEFAULT_REPORT_PATH,
    client: Any | None = None,
    vector_db_path: str | Path | None = None,
    collection_name_mapping: Mapping[str, str] | None = None,
    mapping_file: str | Path | None = DEFAULT_MAPPING_FILE,
) -> list[dict[str, Any]]:
    """生成 Markdown 迁移报告，并返回报告行。"""
    rows = build_legacy_migration_rows(
        client=client,
        vector_db_path=vector_db_path,
        collection_name_mapping=collection_name_mapping,
        mapping_file=mapping_file,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_legacy_migration_markdown(
            rows,
            vector_db_path=vector_db_path or settings.vector_db_path,
        ),
        encoding="utf-8",
    )
    return rows


def render_legacy_migration_markdown(
    rows: list[dict[str, Any]],
    *,
    vector_db_path: str | Path,
    generated_at: datetime | None = None,
) -> str:
    """渲染旧 collection 迁移报告 Markdown。"""
    generated = generated_at or datetime.now()
    lines = [
        "# 旧 Chroma Collection 迁移报告",
        "",
        f"- 生成时间：{generated.isoformat(timespec='seconds')}",
        f"- 扫描目录：`{vector_db_path}`",
        f"- Collection 数量：{len(rows)}",
        "- 默认建议目标：`legacy_admin_only`",
        "- 安全边界：本报告仅执行只读扫描，不删除、不重建、不登记任何 Chroma collection。",
        "",
        "## 迁移原则",
        "",
        "- 不默认公开历史资料库。",
        "- 无旧租户前缀的 collection 先按 `legacy_admin_only` 隐藏待处理。",
        "- 带旧 `tenant_id__collection` 前缀的 collection 仅作为线索，需管理员人工确认后再迁移到用户库。",
        "- 本报告不修改 SQLite `knowledge_bases`，不写入 Chroma，不调用删除或重建接口。",
        "",
        "## 扫描结果",
        "",
        "| collection 名 | original_name | 推断旧租户 | 文档数量 | 建议目标 | 备注 |",
        "|---|---|---:|---:|---|---|",
    ]

    if rows:
        for row in rows:
            lines.append(
                "| {collection_name} | {original_name} | {tenant} | {count} | {target} | {notes} |".format(
                    collection_name=_md_cell(row["collection_name"]),
                    original_name=_md_cell(row["original_name"]),
                    tenant=_md_cell(row["inferred_legacy_tenant"]),
                    count=_md_cell(str(row["document_count"])),
                    target=_md_cell(row["recommended_target"]),
                    notes=_md_cell(row["notes"]),
                )
            )
    else:
        lines.append("| 无 | 无 | default | 0 | legacy_admin_only | 当前未扫描到旧 Chroma collection |")

    lines.extend(
        [
            "",
            "## 人工确认清单",
            "",
            "- 对每个 collection 确认是否仍需要保留。",
            "- 对疑似旧租户前缀的 collection，确认旧租户与现有用户的对应关系。",
            "- 确认后再通过后续迁移步骤登记到 `knowledge_bases`，或保持 `legacy_admin_only`。",
            "",
        ]
    )
    return "\n".join(lines)


def _create_chroma_client(vector_db_path: str | Path | None = None) -> Any:
    """创建 ChromaDB 客户端；仅用于只读列出 collection。"""
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    return chromadb.PersistentClient(
        path=str(vector_db_path or settings.vector_db_path),
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )


def _load_mapping_file(mapping_file: str | Path | None) -> dict[str, str]:
    """读取历史映射文件，兼容 normalized->original 与 original->normalized 两种格式。"""
    if mapping_file is None:
        return {}

    path = Path(mapping_file)
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    mappings = payload.get("mappings", payload) if isinstance(payload, dict) else {}
    if not isinstance(mappings, dict):
        return {}

    return {
        str(key): str(value)
        for key, value in mappings.items()
        if key and value
    }


def _collection_name(collection: Any) -> str:
    """兼容 Chroma Collection 对象和新版 list_collections 字符串返回。"""
    if isinstance(collection, str):
        return collection
    return str(getattr(collection, "name"))


def _collection_metadata(collection: Any) -> dict[str, Any]:
    metadata = getattr(collection, "metadata", None) or {}
    return metadata if isinstance(metadata, dict) else {}


def _collection_document_count(collection: Any) -> int | str:
    count_method = getattr(collection, "count", None)
    if not callable(count_method):
        return "unknown"
    try:
        return int(count_method())
    except Exception:
        return "unknown"


def _resolve_original_name_from_mapping(
    collection_name: str,
    mappings: Mapping[str, str],
) -> str | None:
    """从历史映射中恢复 original_name。"""
    for key, value in sorted(mappings.items()):
        if value == collection_name:
            return key
    mapped_value = mappings.get(collection_name)
    if mapped_value:
        return mapped_value
    return None


def _infer_legacy_tenant(original_name: str) -> str:
    """按旧 tenant_id__collection 规则推断租户；新 registry 前缀不当作旧租户。"""
    if "__" not in original_name:
        return "default"

    possible_tenant, display_name = original_name.split("__", 1)
    if not display_name or possible_tenant in RESERVED_NEW_SCOPE_PREFIXES:
        return "default"

    normalized_tenant = _normalize_legacy_tenant_id(possible_tenant)
    if possible_tenant == normalized_tenant:
        return possible_tenant
    return "default"


def _normalize_legacy_tenant_id(tenant_id: str) -> str:
    safe_tenant_id = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id.strip()).strip("_-").lower()
    return safe_tenant_id or "default"


def _build_notes(original_name: str, inferred_tenant: str) -> str:
    if inferred_tenant != "default":
        return f"疑似旧租户 {inferred_tenant}，需人工确认用户归属"
    if original_name.startswith(("public__", "user__")):
        return "疑似新知识库内部命名，需人工确认是否已迁移"
    return "无旧租户前缀，默认隐藏待管理员确认"


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")

"""旧 Chroma collection 迁移报告测试。"""

from pathlib import Path

from src.shuyixiao_agent.kb import legacy_migration


class _FakeCollection:
    """模拟 Chroma collection 的只读接口。"""

    def __init__(self, name, metadata=None, document_count=0):
        self.name = name
        self.metadata = metadata or {}
        self._document_count = document_count

    def count(self):
        return self._document_count


class _ReadOnlyFakeChromaClient:
    """只允许 list_collections 的假客户端，破坏性方法被调用即失败。"""

    def __init__(self, collections):
        self._collections = collections
        self.destructive_calls = []

    def list_collections(self):
        return list(self._collections)

    def delete_collection(self, name):  # pragma: no cover - 只用于防误调用
        self.destructive_calls.append(("delete_collection", name))
        raise AssertionError("迁移报告生成不能删除 collection")

    def create_collection(self, name, **kwargs):  # pragma: no cover - 只用于防误调用
        self.destructive_calls.append(("create_collection", name, kwargs))
        raise AssertionError("迁移报告生成不能创建 collection")

    def get_or_create_collection(self, name, **kwargs):  # pragma: no cover - 只用于防误调用
        self.destructive_calls.append(("get_or_create_collection", name, kwargs))
        raise AssertionError("迁移报告生成不能重建 collection")


def test_build_legacy_migration_rows_infers_names_tenants_counts_and_default_target():
    """报告行应包含 collection 名、original_name、旧租户、文档数和默认建议目标。"""
    client = _ReadOnlyFakeChromaClient(
        [
            _FakeCollection(
                "tenant_a__contract_templates",
                metadata={"original_name": "tenant_a__合同模板"},
                document_count=7,
            ),
            _FakeCollection(
                "kb_legacy_cn",
                metadata={"hnsw:space": "cosine"},
                document_count=3,
            ),
        ]
    )

    rows = legacy_migration.build_legacy_migration_rows(
        client=client,
        collection_name_mapping={"法规案例库": "kb_legacy_cn"},
    )

    assert rows == [
        {
            "collection_name": "kb_legacy_cn",
            "original_name": "法规案例库",
            "inferred_legacy_tenant": "default",
            "document_count": 3,
            "recommended_target": "legacy_admin_only",
            "notes": "无旧租户前缀，默认隐藏待管理员确认",
        },
        {
            "collection_name": "tenant_a__contract_templates",
            "original_name": "tenant_a__合同模板",
            "inferred_legacy_tenant": "tenant_a",
            "document_count": 7,
            "recommended_target": "legacy_admin_only",
            "notes": "疑似旧租户 tenant_a，需人工确认用户归属",
        },
    ]
    assert client.destructive_calls == []


def test_generate_legacy_migration_report_writes_markdown_without_destructive_actions(tmp_path):
    """生成报告只应写 Markdown 文档，不删除或重建 Chroma collection。"""
    output_path = tmp_path / "legacy-report.md"
    client = _ReadOnlyFakeChromaClient(
        [
            _FakeCollection(
                "tenant_b__rules",
                metadata={"original_name": "tenant_b__规章制度"},
                document_count=2,
            )
        ]
    )

    rows = legacy_migration.generate_legacy_migration_report(
        output_path=output_path,
        client=client,
    )

    content = output_path.read_text(encoding="utf-8")
    assert rows[0]["collection_name"] == "tenant_b__rules"
    assert "| collection 名 | original_name | 推断旧租户 | 文档数量 | 建议目标 | 备注 |" in content
    assert "| tenant_b__rules | tenant_b__规章制度 | tenant_b | 2 | legacy_admin_only |" in content
    assert "本报告仅执行只读扫描，不删除、不重建、不登记任何 Chroma collection。" in content
    assert client.destructive_calls == []


def test_script_and_default_report_document_exist():
    """第 19 步应提供可运行脚本和默认报告文档。"""
    script_path = Path("scripts/generate_legacy_kb_migration_report.py")
    report_path = Path("my_docs/2026-06-10-legacy-kb-migration-report.md")

    assert script_path.exists()
    assert "generate_legacy_migration_report" in script_path.read_text(encoding="utf-8")

    content = report_path.read_text(encoding="utf-8")
    assert "# 旧 Chroma Collection 迁移报告" in content
    assert "legacy_admin_only" in content
    assert "不删除、不重建、不登记" in content

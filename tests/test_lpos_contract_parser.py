"""LPOS 合同解析编排与降级语义测试。"""

import pytest

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.lpos import contract_extractor, contract_parser


def test_parse_contract_file_returns_text_structure_summary_and_metadata(tmp_path):
    contract_file = tmp_path / "contract.txt"
    contract_file.write_text(
        "采购合同\n甲方：A公司\n乙方：B公司\n第一条 付款\n按期付款。",
        encoding="utf-8",
    )

    result = contract_parser.parse_contract_file(
        str(contract_file),
        file_id="20260616_120000_abcdef123456",
        original_filename="contract.txt",
        parse_structure=True,
        include_clause_content=False,
    )

    assert result["text"].startswith("采购合同")
    assert result["document_count"] == 1
    assert result["metadata"]["structure_status"] == "success"
    assert result["contract_structure"]["schema_version"] == "1.0"
    assert result["contract_structure_summary"]["contract_type"] == "采购合同"
    assert "content" not in result["contract_structure"]["clauses"][0]
    assert "page_index" not in result


def test_parse_contract_file_returns_text_only_when_structure_extraction_fails(tmp_path, monkeypatch):
    contract_file = tmp_path / "contract.txt"
    contract_file.write_text("合同正文", encoding="utf-8")
    monkeypatch.setattr(
        contract_extractor,
        "extract_contract_structure",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("extract failed")),
    )

    result = contract_parser.parse_contract_file(
        str(contract_file),
        file_id="20260616_120000_abcdef123456",
        original_filename="contract.txt",
        parse_structure=True,
    )

    assert result["text"] == "合同正文"
    assert result["contract_structure"] is None
    assert result["contract_structure_summary"] is None
    assert result["metadata"]["structure_status"] == "text_only"
    assert any("结构化抽取失败" in warning for warning in result["parse_warnings"])


def test_parse_contract_file_returns_text_only_when_structure_is_disabled(tmp_path):
    contract_file = tmp_path / "contract.txt"
    contract_file.write_text("合同正文", encoding="utf-8")

    result = contract_parser.parse_contract_file(str(contract_file), parse_structure=False)

    assert result["text"] == "合同正文"
    assert result["contract_structure"] is None
    assert result["contract_structure_summary"] is None
    assert result["metadata"]["structure_status"] == "text_only"


def test_parse_contract_file_rejects_empty_text_with_value_error(tmp_path):
    contract_file = tmp_path / "empty.txt"
    contract_file.write_text("   ", encoding="utf-8")

    with pytest.raises(contract_parser.ContractTextExtractionError):
        contract_parser.parse_contract_file(str(contract_file))


def test_web_app_parse_contract_file_delegates_new_parameters(monkeypatch):
    captured = {}

    def fake_parse(file_path, **kwargs):
        captured.update({"file_path": file_path, **kwargs})
        return {"text": "合同正文", "document_count": 1}

    monkeypatch.setattr(contract_parser, "parse_contract_file", fake_parse)

    result = web_app.parse_contract_file(
        "/tmp/contract.txt",
        file_id="20260616_120000_abcdef123456",
        original_filename="contract.txt",
        parse_structure=False,
        include_clause_content=True,
        include_page_index=True,
    )

    assert result["text"] == "合同正文"
    assert captured == {
        "file_path": "/tmp/contract.txt",
        "file_id": "20260616_120000_abcdef123456",
        "original_filename": "contract.txt",
        "parse_structure": False,
        "include_clause_content": True,
        "include_page_index": True,
    }

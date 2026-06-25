"""LPOS 合同结构化抽取规则测试。"""

from textwrap import dedent

from langchain_core.documents import Document

from src.shuyixiao_agent.lpos import contract_extractor, pageindex


def _blocks_from_text(text: str):
    """从测试文本构建 pageindex 文本块。"""
    normalized_text = dedent(text).strip()
    return pageindex.build_page_index(
        [Document(page_content=normalized_text, metadata={"type": "text"})],
        file_id="20260616_120000_abcdef123456",
        original_filename="合同.txt",
        document_type="text",
    )


def test_extract_contract_structure_detects_type_parties_amount_term_and_clauses():
    blocks = _blocks_from_text(
        """
        采购合同
        甲方：北京示例科技有限公司
        乙方：上海示例供应链有限公司
        合同总价为人民币100万元。
        履行期限：2026年7月1日至2027年6月30日。

        第一条 标的物
        乙方向甲方供应软件服务。

        第二条 付款方式
        甲方应在收到发票后10日内付款。

        第三条 违约责任
        任一方违约应承担赔偿责任。
        """
    )

    result = contract_extractor.extract_contract_structure(
        blocks,
        file_id="20260616_120000_abcdef123456",
        original_filename="采购合同.txt",
        document_type="text",
        include_clause_content=False,
    )

    assert result.structure_status == "success"
    assert result.contract_type["value"] == "采购合同"
    assert any("北京示例科技有限公司" in item["value"] for item in result.key_fields["parties"])
    assert any("100万元" in item["value"] for item in result.key_fields["amount"])
    assert any("2026年7月1日" in item["value"] for item in result.key_fields["term"])
    assert [clause.clause_id for clause in result.clauses] == [
        "clause_0001",
        "clause_0002",
        "clause_0003",
    ]
    assert result.clauses[1].title == "付款方式"
    assert "content" not in result.clauses[1].to_api_dict(include_content=False)


def test_extract_contract_structure_handles_rental_docx_title_parties_and_sections():
    blocks = _blocks_from_text(
        """
        租 赁 合 同
        甲方（承租方）：              张三
        乙方（出租方）：  沙漠之洲帐篷俱乐部

        一、合同租赁物
        本合同的租赁物为帐篷以及配件。

        二、租赁期限
        租赁期限暂定为1天。

        三、租金、相关费用及支付
        承租方需交纳人民币100元押金。

        四、租赁物权属
        租赁物所有权属于乙方。

        五、合同效力及其他
        本合同自甲乙双方签字之日起生效。
        """
    )

    result = contract_extractor.extract_contract_structure(
        blocks,
        file_id="20260616_120000_abcdef123456",
        original_filename="产品租赁合同范本.docx",
        document_type="docx",
        include_clause_content=False,
    )

    assert result.contract_type["value"] == "租赁合同"
    assert any("甲方（承租方）：张三" in item["value"] for item in result.key_fields["parties"])
    assert any("乙方（出租方）：沙漠之洲帐篷俱乐部" in item["value"] for item in result.key_fields["parties"])
    assert [clause.title for clause in result.clauses[:5]] == [
        "合同租赁物",
        "租赁期限",
        "租金、相关费用及支付",
        "租赁物权属",
        "合同效力及其他",
    ]
    assert len(result.key_clause_summary) >= 2


def test_extract_contract_structure_uses_filename_as_contract_type_fallback():
    blocks = _blocks_from_text(
        """
        合同范本
        甲方：张三
        乙方：李四
        """
    )

    result = contract_extractor.extract_contract_structure(
        blocks,
        file_id="20260616_120000_abcdef123456",
        original_filename="产品租赁合同范本.docx",
        document_type="docx",
    )

    assert result.contract_type["value"] == "租赁合同"


def test_extract_contract_structure_truncates_clause_preview_and_warns_when_clause_limit_exceeded():
    blocks = _blocks_from_text("\n\n".join(f"第{i}条 条款{i}\n" + ("正文" * 100) for i in range(1, 6)))

    result = contract_extractor.extract_contract_structure(
        blocks,
        file_id="20260616_120000_abcdef123456",
        original_filename="合同.txt",
        document_type="text",
        max_clauses=3,
        clause_preview_chars=20,
    )

    assert len(result.clauses) == 3
    assert result.clauses[0].content_truncated is True
    assert len(result.clauses[0].content_preview) <= 20
    assert any("超过条款数量上限" in warning for warning in result.warnings)

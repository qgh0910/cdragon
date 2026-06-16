"""多智能体 RAG query 压缩测试。"""

from langchain_core.documents import Document

from src.shuyixiao_agent.agents.multi_agent_collaboration import (
    AgentProfile,
    AgentRole,
    MultiAgentCollaboration,
)


class _FakeLLM:
    """避免测试触发真实 LLM。"""

    def simple_chat(self, prompt, timeout=None):
        return "ok"


class _CapturingRAGAgent:
    """记录传入检索器的 query，避免触发真实 RAG/embedding。"""

    def __init__(self, documents=None):
        self.queries = []
        self.documents = documents or []

    def retrieve(self, query, top_k=None, mode=None, use_rerank=True):
        self.queries.append(
            {
                "query": query,
                "top_k": top_k,
                "mode": mode,
                "use_rerank": use_rerank,
            }
        )
        return self.documents

    def format_documents_for_prompt(self, documents):
        return "\n".join(doc.page_content for doc in documents)


def _collaboration(rag_agent=None):
    return MultiAgentCollaboration(
        llm_client=_FakeLLM(),
        verbose=False,
        rag_agent=rag_agent,
    )


def _agent(name="legal_researcher", role=AgentRole.ADVISOR):
    return AgentProfile(
        name=name,
        role=role,
        description=name,
        expertise=[name],
        system_prompt="",
        enable_rag=True,
    )


def test_legal_researcher_rag_query_is_compacted_for_long_contract():
    """超长合同不能原样进入 legal_researcher 的 RAG query。"""
    collaboration = _collaboration()
    agent = _agent("legal_researcher", AgentRole.ADVISOR)
    long_contract = (
        "采购合同\n"
        "甲方：北京示例科技有限公司\n"
        "乙方：上海示例供应链有限公司\n"
        "第一条 标的物\n"
        "第二条 付款方式\n"
        "第三条 违约责任\n"
        + ("这是超长合同正文，用于模拟完整上传文件解析结果。" * 2000)
    )

    query = collaboration._build_rag_query(agent, long_contract, context=None)

    assert len(query) <= collaboration.RAG_QUERY_MAX_CHARS
    assert "法律法规" in query
    assert "司法解释" in query
    assert "判例" in query
    assert "合同审查" in query
    assert "第一条 标的物" in query
    assert "第二条 付款方式" in query
    assert "第三条 违约责任" in query
    assert query.count("这是超长合同正文") < 20


def test_rag_query_uses_context_summary_instead_of_full_json_dump():
    """超大 context 只能摘要进入 query，不能完整 JSON dump。"""
    collaboration = _collaboration()
    agent = _agent("legal_researcher", AgentRole.ADVISOR)
    context = {
        "contract_type": "采购合同",
        "review_focus": "违约责任和争议解决",
        "industry": "软件服务",
        "parsed_text": "不得完整进入 query。" * 2000,
        "raw_text": "原始全文也不得完整进入 query。" * 2000,
    }

    query = collaboration._build_rag_query(agent, "请审查合同", context=context)

    assert len(query) <= collaboration.RAG_QUERY_MAX_CHARS
    assert "采购合同" in query
    assert "违约责任和争议解决" in query
    assert "软件服务" in query
    assert query.count("不得完整进入 query。") <= 2
    assert query.count("原始全文也不得完整进入 query。") <= 2
    assert '"parsed_text"' not in query
    assert '"raw_text"' not in query


def test_rag_query_prefix_depends_on_agent_name():
    """法律检索和合规审查 Agent 应保留不同检索意图。"""
    collaboration = _collaboration()
    legal_agent = _agent("legal_researcher", AgentRole.ADVISOR)
    compliance_agent = _agent("compliance_checker", AgentRole.REVIEWER)
    generic_agent = _agent("other_rag_agent", AgentRole.SPECIALIST)

    legal_query = collaboration._build_rag_query(legal_agent, "审查采购合同", None)
    compliance_query = collaboration._build_rag_query(
        compliance_agent, "审查采购合同", None
    )
    generic_query = collaboration._build_rag_query(generic_agent, "审查采购合同", None)

    assert "法律法规" in legal_query
    assert "司法解释" in legal_query
    assert "判例" in legal_query
    assert "监管规则" in compliance_query
    assert "合规要求" in compliance_query
    assert "企业红线" in compliance_query
    assert "任务检索" in generic_query
    assert legal_query != compliance_query
    assert compliance_query != generic_query


def test_build_rag_context_sends_compacted_query_to_retriever():
    """_build_rag_context 传给 RAGAgent.retrieve 的 query 必须已经压缩。"""
    rag_agent = _CapturingRAGAgent(
        documents=[
            Document(
                page_content="民法典合同编相关依据",
                metadata={"source": "civil-code.md"},
            )
        ]
    )
    collaboration = _collaboration(rag_agent=rag_agent)
    agent = _agent("legal_researcher", AgentRole.ADVISOR)

    context_text = "完整解析文本" * 3000
    result = collaboration._build_rag_context(
        agent,
        "租赁合同\n第一条 租赁物\n第二条 租金\n" + ("超长正文" * 3000),
        context={"parsed_text": context_text, "contract_type": "房屋租赁合同"},
    )

    assert "民法典合同编相关依据" in result
    assert len(rag_agent.queries) == 1
    captured_query = rag_agent.queries[0]["query"]
    assert len(captured_query) <= collaboration.RAG_QUERY_MAX_CHARS
    assert "第一条 租赁物" in captured_query
    assert "房屋租赁合同" in captured_query
    assert captured_query.count("完整解析文本") <= 2
    assert rag_agent.queries[0]["use_rerank"] is True


def test_full_input_text_is_preserved_for_agent_response():
    """RAG query 压缩不能截断主流程传给 LLM 的合同全文。"""
    long_contract = "合同全文开始\n" + ("重要合同正文" * 3000) + "\n合同全文结束"
    captured = {}

    class _RecordingLLM:
        def simple_chat(self, prompt, timeout=None):
            captured["prompt"] = prompt
            return "审查完成"

    collaboration = MultiAgentCollaboration(
        llm_client=_RecordingLLM(),
        verbose=False,
        rag_agent=None,
    )
    agent = _agent("contract_reviewer", AgentRole.COORDINATOR)
    collaboration.register_agent(agent)

    response = collaboration.get_agent_response("contract_reviewer", long_contract)

    assert response == "审查完成"
    sent_content = captured["prompt"]
    assert "合同全文开始" in sent_content
    assert "合同全文结束" in sent_content
    assert sent_content.count("重要合同正文") == 3000

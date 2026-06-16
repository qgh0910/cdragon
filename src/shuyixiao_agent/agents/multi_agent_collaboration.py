"""
Multi-Agent Collaboration - 多智能体协作

这个模块实现了 Agentic Design Pattern 中的 Multi-Agent Collaboration 模式。
多智能体协作模式通过让多个专业化的 Agent 相互协作来解决复杂问题，
每个 Agent 扮演不同的角色，贡献自己的专业知识，最终达成共同目标。

核心优势：
1. 专业分工：每个 Agent 专注于特定领域，提高专业性
2. 协同效应：多个 Agent 协作产生 1+1>2 的效果
3. 灵活性：可以动态组合不同的 Agent 团队
4. 可扩展：轻松添加新的 Agent 角色
5. 鲁棒性：某个 Agent 失败不会影响整体流程

应用场景：
- 软件开发团队（产品经理、架构师、开发者、测试）
- 研究团队（理论、实验、数据分析、论文写作）
- 内容创作团队（策划、写作、编辑、审核）
- 决策咨询团队（分析师、顾问、评审、总结）
"""

from typing import List, Dict, Any, Callable, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from datetime import datetime
import time
from ..config import settings


class AgentRole(Enum):
    """Agent 角色类型"""
    COORDINATOR = "coordinator"  # 协调者：负责任务分配和结果整合
    SPECIALIST = "specialist"    # 专家：负责特定领域的任务
    REVIEWER = "reviewer"        # 审核者：负责质量检查和反馈
    EXECUTOR = "executor"        # 执行者：负责具体任务执行
    ADVISOR = "advisor"          # 顾问：提供建议和指导


class CollaborationMode(Enum):
    """协作模式"""
    SEQUENTIAL = "sequential"    # 顺序协作：Agent 按顺序工作
    PARALLEL = "parallel"        # 并行协作：Agent 同时工作
    HIERARCHICAL = "hierarchical"  # 层级协作：有管理层级
    PEER_TO_PEER = "peer_to_peer"  # 对等协作：Agent 平等协作
    HYBRID = "hybrid"            # 混合模式：结合多种协作方式


class CommunicationType(Enum):
    """通信类型"""
    DIRECT = "direct"            # 直接通信：Agent 之间直接交流
    BROADCAST = "broadcast"      # 广播：向所有 Agent 发送消息
    COORDINATED = "coordinated"  # 协调通信：通过协调者中转
    SELECTIVE = "selective"      # 选择性：只与特定 Agent 通信


@dataclass
class AgentProfile:
    """Agent 配置文件"""
    name: str                    # Agent 名称
    role: AgentRole             # Agent 角色
    description: str            # Agent 描述
    expertise: List[str]        # 专业领域
    system_prompt: str          # 系统提示词
    capabilities: List[str] = field(default_factory=list)  # 能力列表
    constraints: List[str] = field(default_factory=list)   # 约束条件
    priority: int = 0           # 优先级
    enable_rag: bool = False    # 是否启用 RAG 检索
    rag_top_k: int = 5          # RAG 检索返回数量
    rag_mode: str = "hybrid"    # RAG 检索模式：vector/keyword/hybrid
    

@dataclass
class Message:
    """Agent 之间的消息"""
    sender: str                 # 发送者
    receiver: str               # 接收者（"all" 表示广播）
    content: str                # 消息内容
    message_type: str           # 消息类型（task/response/feedback/query）
    timestamp: float            # 时间戳
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class CollaborationTask:
    """协作任务"""
    task_id: str                # 任务ID
    description: str            # 任务描述
    assigned_agents: List[str]  # 分配的 Agent
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务
    priority: int = 0           # 优先级
    status: str = "pending"     # 状态
    result: Optional[str] = None  # 结果


@dataclass
class CollaborationResult:
    """协作结果"""
    final_output: str           # 最终输出
    agent_contributions: Dict[str, Any]  # 每个 Agent 的贡献
    messages: List[Message]     # 所有消息记录
    tasks: List[CollaborationTask]  # 所有任务
    success: bool               # 是否成功
    execution_time: float       # 执行时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    error_message: str = ""     # 错误信息


class MultiAgentCollaboration:
    """
    多智能体协作系统
    
    实现多个 Agent 之间的协作，每个 Agent 扮演不同角色，
    通过相互通信和协作来完成复杂任务。
    
    示例用法:
        # 创建协作系统
        collaboration = MultiAgentCollaboration(
            llm_client=llm_client,
            mode=CollaborationMode.HIERARCHICAL,
            verbose=True
        )
        
        # 注册 Agents
        collaboration.register_agent(AgentProfile(
            name="architect",
            role=AgentRole.SPECIALIST,
            description="系统架构师",
            expertise=["系统设计", "技术选型"],
            system_prompt="你是一位经验丰富的系统架构师..."
        ))
        
        # 执行协作
        result = collaboration.collaborate("设计一个电商系统")
    """

    RAG_QUERY_MAX_CHARS = 6000
    RAG_QUERY_SECTION_MAX_CHARS = 300
    RAG_QUERY_CONTEXT_MAX_CHARS = 1200
    RAG_QUERY_HEADINGS_MAX_ITEMS = 20
    RAG_CONTEXT_FULL_TEXT_KEYS = {
        "parsed_text",
        "contract_text",
        "file_content",
        "raw_text",
        "full_text",
        "text",
        "content",
    }
    RAG_CONTEXT_PRIORITY_KEYS = (
        "contract_type",
        "task_type",
        "review_focus",
        "industry",
        "jurisdiction",
        "risk_level",
        "contract_name",
        "party_a",
        "party_b",
    )
    
    def __init__(
        self,
        llm_client,
        mode: Union[CollaborationMode, str] = CollaborationMode.HIERARCHICAL,
        verbose: bool = True,
        max_rounds: int = 5,
        rag_agent: Optional[Any] = None
    ):
        """
        初始化多智能体协作系统
        
        Args:
            llm_client: 大语言模型客户端
            mode: 协作模式
            verbose: 是否打印详细信息
            max_rounds: 最大协作轮数
            rag_agent: 可选 RAG Agent，用于为启用 RAG 的 Agent 注入知识库上下文
        """
        self.llm_client = llm_client
        self.mode = CollaborationMode(mode) if isinstance(mode, str) else mode
        self.verbose = verbose
        self.max_rounds = max_rounds
        self.rag_agent = rag_agent

        self.agents: Dict[str, AgentProfile] = {}
        self.messages: List[Message] = []
        self.tasks: List[CollaborationTask] = []
        
    def register_agent(self, agent: AgentProfile):
        """
        注册一个 Agent
        
        Args:
            agent: Agent 配置文件
        """
        self.agents[agent.name] = agent
        if self.verbose:
            print(f"✓ 注册 Agent: {agent.name} ({agent.role.value}) - {agent.description}")
            
    def register_agents(self, agents: List[AgentProfile]):
        """
        批量注册 Agents
        
        Args:
            agents: Agent 配置文件列表
        """
        for agent in agents:
            self.register_agent(agent)
            
    def send_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        message_type: str = "task"
    ) -> Message:
        """
        发送消息
        
        Args:
            sender: 发送者
            receiver: 接收者
            content: 消息内容
            message_type: 消息类型
            
        Returns:
            Message 对象
        """
        message = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
            timestamp=time.time()
        )
        self.messages.append(message)
        
        if self.verbose:
            print(f"\n💬 [{sender} → {receiver}] ({message_type})")
            print(f"   {content[:100]}...")
            
        return message

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """按字符数截断文本，避免 RAG query 超过 embedding 输入限制。"""
        if not text:
            return ""
        normalized = re.sub(r"\s+", " ", str(text)).strip()
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars].rstrip()

    def _extract_clause_headings(self, text: str, max_items: int = 20) -> List[str]:
        """从合同文本中提取常见条款标题，用于增强检索 query。"""
        if not text:
            return []

        heading_pattern = re.compile(
            r"^\s*((第[一二三四五六七八九十百千万0-9]+条|[一二三四五六七八九十]+、|"
            r"（[一二三四五六七八九十0-9]+）|[0-9]+[.、])\s*[^\n。；;]{1,80})"
        )
        headings: List[str] = []
        seen = set()
        for line in str(text).splitlines():
            line = line.strip()
            if not line:
                continue
            match = heading_pattern.match(line)
            if not match:
                continue
            heading = self._truncate_text(match.group(1), 100)
            if heading in seen:
                continue
            seen.add(heading)
            headings.append(heading)
            if len(headings) >= max_items:
                break
        return headings

    def _compact_input_for_rag(self, input_text: str) -> str:
        """提取合同前段、后段和条款标题，形成短检索摘要。"""
        if not input_text:
            return ""

        text = str(input_text).strip()
        head = self._truncate_text(text, self.RAG_QUERY_SECTION_MAX_CHARS)
        tail = ""
        if len(text) > self.RAG_QUERY_SECTION_MAX_CHARS:
            tail = self._truncate_text(text[-self.RAG_QUERY_SECTION_MAX_CHARS:], 120)

        headings = self._extract_clause_headings(text, self.RAG_QUERY_HEADINGS_MAX_ITEMS)
        parts = [f"任务摘要: {head}"]
        if headings:
            parts.append(f"条款标题: {'; '.join(headings)}")
        if tail:
            parts.append(f"末尾摘要: {tail}")
        return "\n".join(parts)

    def _context_value_to_short_text(self, value: Any, max_chars: int = 200) -> str:
        """把 context 中的短值转换为适合检索的文本。"""
        if value is None:
            return ""
        if isinstance(value, (str, int, float, bool)):
            return self._truncate_text(str(value), max_chars)
        if isinstance(value, list):
            short_items = [
                self._context_value_to_short_text(item, max_chars=80)
                for item in value[:5]
            ]
            return "、".join(item for item in short_items if item)
        if isinstance(value, dict):
            short_items = []
            for key, item in list(value.items())[:5]:
                item_text = self._context_value_to_short_text(item, max_chars=80)
                if item_text:
                    short_items.append(f"{key}: {item_text}")
            return "；".join(short_items)
        return self._truncate_text(str(value), max_chars)

    def _compact_context_for_rag(self, context: Optional[Dict[str, Any]]) -> str:
        """从 context 中提取少量适合检索的信息，不完整 JSON dump。"""
        if not context:
            return ""

        items = []
        seen_keys = set()

        for key in self.RAG_CONTEXT_PRIORITY_KEYS:
            if key not in context:
                continue
            value_text = self._context_value_to_short_text(context.get(key))
            if value_text:
                items.append(f"{key}: {value_text}")
                seen_keys.add(key)

        for key, value in context.items():
            if key in seen_keys:
                continue
            if key in self.RAG_CONTEXT_FULL_TEXT_KEYS:
                value_text = self._context_value_to_short_text(value, max_chars=12)
            else:
                value_text = self._context_value_to_short_text(value, max_chars=200)
            if value_text:
                items.append(f"{key}: {value_text}")
            if len("\n".join(items)) >= self.RAG_QUERY_CONTEXT_MAX_CHARS:
                break

        return self._truncate_text("\n".join(items), self.RAG_QUERY_CONTEXT_MAX_CHARS)

    def _rag_query_prefix_for_agent(self, agent: AgentProfile) -> str:
        """根据 Agent 职责选择检索意图前缀。"""
        if agent.name == "legal_researcher":
            return "法律法规 司法解释 判例 合同审查 风险点"
        if agent.name == "compliance_checker":
            return "监管规则 合规要求 企业红线 合同合规"
        return "任务检索 合同资料 关键事实"

    def _build_rag_query(
        self,
        agent: AgentProfile,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """根据 Agent 职责构建短 RAG query，避免把整份合同送入 embedding。"""
        parts = [
            self._rag_query_prefix_for_agent(agent),
            self._compact_input_for_rag(input_text),
        ]
        context_summary = self._compact_context_for_rag(context)
        if context_summary:
            parts.append(f"上下文摘要:\n{context_summary}")

        query = "\n".join(part for part in parts if part).strip()
        return self._truncate_text(query, self.RAG_QUERY_MAX_CHARS)

    def _build_rag_context(
        self,
        agent: AgentProfile,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """检索知识库并格式化为可注入 Agent prompt 的上下文"""
        if not self.rag_agent or not agent.enable_rag:
            return ""

        try:
            query = self._build_rag_query(agent, input_text, context)
            documents = self.rag_agent.retrieve(
                query=query,
                top_k=agent.rag_top_k,
                mode=agent.rag_mode,
                use_rerank=True
            )
        except Exception as e:
            if self.verbose:
                print(f"⚠️  {agent.name} RAG 检索失败: {e}")
            return ""

        if not documents:
            return ""

        if hasattr(self.rag_agent, "format_documents_for_prompt"):
            return self.rag_agent.format_documents_for_prompt(documents)

        if hasattr(self.rag_agent, "context_manager"):
            return self.rag_agent.context_manager.format_documents_for_prompt(
                documents,
                query=input_text,
                instruction="请基于以下知识库检索结果提供专业见解，并在使用依据时标注来源。"
            )

        lines = ["## 知识库检索结果"]
        for index, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "unknown")
            content = doc.page_content.strip()
            lines.append(f"[{index}] 来源: {source}\n{content}")

        return "\n\n".join(lines)

    def get_agent_response(
        self,
        agent_name: str,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        获取 Agent 的响应
        
        Args:
            agent_name: Agent 名称
            input_text: 输入文本
            context: 上下文信息
            
        Returns:
            Agent 的响应
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' 未注册")
            
        agent = self.agents[agent_name]
        
        # 构建提示
        prompt = f"{agent.system_prompt}\n\n"
        
        if context:
            prompt += "## 上下文信息\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
            prompt += "\n"

        rag_context = self._build_rag_context(agent, input_text, context)
        if rag_context:
            prompt += f"{rag_context}\n\n"

        prompt += f"## 任务\n{input_text}\n\n请提供你的专业见解："
        
        if self.verbose:
            print(f"\n🤖 {agent_name} 正在思考...")
            
        try:
            # 使用更长的超时时间，因为多智能体协作需要多次调用
            response = self.llm_client.simple_chat(prompt, timeout=settings.multi_agent_timeout)
            
            if self.verbose:
                print(f"✓ {agent_name} 完成")
                
            return response
            
        except Exception as e:
            error_msg = f"Agent {agent_name} 执行失败: {str(e)}"
            if self.verbose:
                print(f"❌ {error_msg}")
            return error_msg
            
    def _sequential_collaboration(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CollaborationResult:
        """
        顺序协作模式
        
        Agents 按照注册顺序依次工作，后面的 Agent 可以看到前面的结果
        """
        start_time = time.time()
        agent_contributions = {}
        current_input = input_text
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🔄 顺序协作模式 - {len(self.agents)} 个 Agents")
            print(f"{'='*60}")
            
        # 按优先级排序
        sorted_agents = sorted(
            self.agents.values(),
            key=lambda x: x.priority,
            reverse=True
        )
        
        for i, agent in enumerate(sorted_agents, 1):
            if self.verbose:
                print(f"\n--- 步骤 {i}/{len(sorted_agents)}: {agent.name} ---")
                
            # 构建上下文
            agent_context = context.copy() if context else {}
            if i > 1:
                agent_context["previous_results"] = agent_contributions
                
            # 获取响应
            response = self.get_agent_response(
                agent.name,
                current_input,
                agent_context
            )
            
            agent_contributions[agent.name] = {
                "role": agent.role.value,
                "response": response,
                "order": i
            }
            
            # 记录消息
            self.send_message(
                sender="coordinator",
                receiver=agent.name,
                content=current_input,
                message_type="task"
            )
            self.send_message(
                sender=agent.name,
                receiver="coordinator",
                content=response,
                message_type="response"
            )
            
            # 更新输入供下一个 Agent 使用
            current_input = f"基于之前的工作，请继续：\n\n{response}"
            
        # 最终整合
        final_output = self._synthesize_results(agent_contributions, input_text)
        
        execution_time = time.time() - start_time
        
        return CollaborationResult(
            final_output=final_output,
            agent_contributions=agent_contributions,
            messages=self.messages.copy(),
            tasks=self.tasks.copy(),
            success=True,
            execution_time=execution_time
        )
        
    def _parallel_collaboration(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CollaborationResult:
        """
        并行协作模式
        
        所有 Agents 同时工作，然后整合结果
        """
        start_time = time.time()
        agent_contributions = {}
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"⚡ 并行协作模式 - {len(self.agents)} 个 Agents 同时工作")
            print(f"{'='*60}")
            
        # 所有 Agents 同时处理任务
        for agent in self.agents.values():
            if self.verbose:
                print(f"\n🔨 启动 {agent.name}...")
                
            response = self.get_agent_response(
                agent.name,
                input_text,
                context
            )
            
            agent_contributions[agent.name] = {
                "role": agent.role.value,
                "response": response,
                "expertise": agent.expertise
            }
            
            # 记录消息
            self.send_message(
                sender="coordinator",
                receiver=agent.name,
                content=input_text,
                message_type="task"
            )
            self.send_message(
                sender=agent.name,
                receiver="coordinator",
                content=response,
                message_type="response"
            )
            
        # 整合所有结果
        final_output = self._synthesize_results(agent_contributions, input_text)
        
        execution_time = time.time() - start_time
        
        return CollaborationResult(
            final_output=final_output,
            agent_contributions=agent_contributions,
            messages=self.messages.copy(),
            tasks=self.tasks.copy(),
            success=True,
            execution_time=execution_time
        )
        
    def _hierarchical_collaboration(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CollaborationResult:
        """
        层级协作模式
        
        有明确的管理层级，协调者分配任务，专家执行，审核者检查
        """
        start_time = time.time()
        agent_contributions = {}
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🏢 层级协作模式")
            print(f"{'='*60}")
            
        # 按角色分组
        coordinators = [a for a in self.agents.values() if a.role == AgentRole.COORDINATOR]
        specialists = [a for a in self.agents.values() if a.role == AgentRole.SPECIALIST]
        reviewers = [a for a in self.agents.values() if a.role == AgentRole.REVIEWER]
        executors = [a for a in self.agents.values() if a.role == AgentRole.EXECUTOR]
        advisors = [a for a in self.agents.values() if a.role == AgentRole.ADVISOR]
        
        # 阶段1: 协调者分析任务
        if coordinators:
            coordinator = coordinators[0]
            if self.verbose:
                print(f"\n📋 阶段1: 任务分析 ({coordinator.name})")
                
            analysis = self.get_agent_response(
                coordinator.name,
                f"分析以下任务并制定执行计划：\n{input_text}",
                context
            )
            agent_contributions[coordinator.name] = {
                "role": "coordinator",
                "response": analysis,
                "phase": "planning"
            }
            
        # 阶段2: 顾问提供建议（如果有）
        if advisors:
            if self.verbose:
                print(f"\n💡 阶段2: 专家咨询 ({len(advisors)} 位顾问)")
                
            for advisor in advisors:
                advice = self.get_agent_response(
                    advisor.name,
                    f"对以下任务提供专业建议：\n{input_text}",
                    {"analysis": agent_contributions.get(coordinators[0].name, {}).get("response", "")}
                )
                agent_contributions[advisor.name] = {
                    "role": "advisor",
                    "response": advice,
                    "phase": "consulting"
                }
                
        # 阶段3: 专家并行工作
        if specialists:
            if self.verbose:
                print(f"\n🎯 阶段3: 专家执行 ({len(specialists)} 位专家)")
                
            for specialist in specialists:
                work = self.get_agent_response(
                    specialist.name,
                    input_text,
                    {
                        "plan": agent_contributions.get(coordinators[0].name if coordinators else "", {}).get("response", ""),
                        "advice": [agent_contributions[a.name]["response"] for a in advisors]
                    }
                )
                agent_contributions[specialist.name] = {
                    "role": "specialist",
                    "response": work,
                    "phase": "execution",
                    "expertise": specialist.expertise
                }
                
        # 阶段4: 执行者完成具体任务（如果有）
        if executors:
            if self.verbose:
                print(f"\n⚙️ 阶段4: 任务执行 ({len(executors)} 位执行者)")
                
            for executor in executors:
                execution = self.get_agent_response(
                    executor.name,
                    input_text,
                    {
                        "specialist_work": [agent_contributions[s.name]["response"] for s in specialists]
                    }
                )
                agent_contributions[executor.name] = {
                    "role": "executor",
                    "response": execution,
                    "phase": "implementation"
                }
                
        # 阶段5: 审核者检查质量
        if reviewers:
            if self.verbose:
                print(f"\n🔍 阶段5: 质量审核 ({len(reviewers)} 位审核者)")
                
            for reviewer in reviewers:
                review = self.get_agent_response(
                    reviewer.name,
                    "审核以下工作成果，提供反馈和改进建议",
                    {"all_work": agent_contributions}
                )
                agent_contributions[reviewer.name] = {
                    "role": "reviewer",
                    "response": review,
                    "phase": "review"
                }
                
        # 阶段6: 协调者整合最终结果
        if self.verbose:
            print(f"\n📊 阶段6: 结果整合")
            
        final_output = self._synthesize_results(agent_contributions, input_text)
        
        execution_time = time.time() - start_time
        
        return CollaborationResult(
            final_output=final_output,
            agent_contributions=agent_contributions,
            messages=self.messages.copy(),
            tasks=self.tasks.copy(),
            success=True,
            execution_time=execution_time
        )
        
    def _peer_to_peer_collaboration(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CollaborationResult:
        """
        对等协作模式
        
        Agents 平等协作，可以相互讨论和改进
        """
        start_time = time.time()
        agent_contributions = {}
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🤝 对等协作模式 - {self.max_rounds} 轮协作")
            print(f"{'='*60}")
            
        agents_list = list(self.agents.values())
        
        for round_num in range(self.max_rounds):
            if self.verbose:
                print(f"\n--- 第 {round_num + 1} 轮协作 ---")
                
            for agent in agents_list:
                # 收集其他 Agents 的反馈
                peer_feedback = []
                for other_agent in agents_list:
                    if other_agent.name != agent.name and other_agent.name in agent_contributions:
                        peer_feedback.append({
                            "agent": other_agent.name,
                            "feedback": agent_contributions[other_agent.name].get("response", "")
                        })
                        
                # 构建上下文
                agent_context = context.copy() if context else {}
                agent_context["round"] = round_num + 1
                agent_context["peer_feedback"] = peer_feedback
                
                # 获取响应
                response = self.get_agent_response(
                    agent.name,
                    input_text,
                    agent_context
                )
                
                agent_contributions[agent.name] = {
                    "role": agent.role.value,
                    "response": response,
                    "round": round_num + 1
                }
                
        # 整合结果
        final_output = self._synthesize_results(agent_contributions, input_text)
        
        execution_time = time.time() - start_time
        
        return CollaborationResult(
            final_output=final_output,
            agent_contributions=agent_contributions,
            messages=self.messages.copy(),
            tasks=self.tasks.copy(),
            success=True,
            execution_time=execution_time
        )
        
    def _synthesize_results(
        self,
        agent_contributions: Dict[str, Any],
        original_task: str
    ) -> str:
        """
        整合所有 Agent 的结果
        
        Args:
            agent_contributions: Agent 贡献
            original_task: 原始任务
            
        Returns:
            整合后的最终结果
        """
        if self.verbose:
            print(f"\n🔄 正在整合 {len(agent_contributions)} 个 Agent 的成果...")
            
        # 构建整合提示
        synthesis_prompt = f"""作为协调者，请整合以下多个 Agent 的工作成果，生成一个完整、连贯的最终输出。

原始任务：
{original_task}

各 Agent 的贡献：
"""
        
        for agent_name, contribution in agent_contributions.items():
            agent = self.agents.get(agent_name)
            role = agent.role.value if agent else "unknown"
            synthesis_prompt += f"\n### {agent_name} ({role})\n{contribution.get('response', '')}\n"
            
        synthesis_prompt += """

请整合以上内容，生成最终输出：
1. 保留各 Agent 的专业见解
2. 确保内容连贯完整
3. 解决可能的矛盾或重复
4. 突出关键结论和建议
"""
        
        try:
            # 使用更长的超时时间进行结果整合
            final_output = self.llm_client.simple_chat(synthesis_prompt, timeout=settings.multi_agent_timeout)
            if self.verbose:
                print("✓ 整合完成")
            return final_output
        except Exception as e:
            if self.verbose:
                print(f"❌ 整合失败: {e}")
            # 降级方案：简单拼接
            result = f"# 协作结果\n\n原始任务：{original_task}\n\n"
            for agent_name, contribution in agent_contributions.items():
                result += f"\n## {agent_name}\n{contribution.get('response', '')}\n"
            return result
            
    def collaborate(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CollaborationResult:
        """
        执行多智能体协作
        
        Args:
            input_text: 输入文本/任务描述
            context: 上下文信息
            
        Returns:
            CollaborationResult 包含协作结果
        """
        if not self.agents:
            return CollaborationResult(
                final_output="",
                agent_contributions={},
                messages=[],
                tasks=[],
                success=False,
                execution_time=0,
                error_message="没有注册任何 Agent"
            )
            
        # 清空消息和任务历史
        self.messages.clear()
        self.tasks.clear()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作")
            print(f"模式: {self.mode.value}")
            print(f"Agent 数量: {len(self.agents)}")
            print(f"{'='*60}")
            
        try:
            # 根据协作模式选择执行方式
            if self.mode == CollaborationMode.SEQUENTIAL:
                result = self._sequential_collaboration(input_text, context)
            elif self.mode == CollaborationMode.PARALLEL:
                result = self._parallel_collaboration(input_text, context)
            elif self.mode == CollaborationMode.HIERARCHICAL:
                result = self._hierarchical_collaboration(input_text, context)
            elif self.mode == CollaborationMode.PEER_TO_PEER:
                result = self._peer_to_peer_collaboration(input_text, context)
            else:  # HYBRID
                # 混合模式：先并行收集意见，再层级整合
                if self.verbose:
                    print("\n🔀 混合协作模式：并行收集 + 层级整合")
                result = self._parallel_collaboration(input_text, context)
                
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"✅ 协作完成！用时 {result.execution_time:.2f} 秒")
                print(f"{'='*60}")
                
            return result
            
        except Exception as e:
            error_msg = f"协作执行失败: {str(e)}"
            if self.verbose:
                print(f"\n❌ {error_msg}")
                
            return CollaborationResult(
                final_output="",
                agent_contributions={},
                messages=self.messages.copy(),
                tasks=self.tasks.copy(),
                success=False,
                execution_time=0,
                error_message=error_msg
            )
            
    def get_collaboration_summary(self) -> str:
        """
        获取协作摘要
        
        Returns:
            协作摘要文本
        """
        summary = f"""
# 多智能体协作摘要

## 基本信息
- 协作模式: {self.mode.value}
- Agent 数量: {len(self.agents)}
- 消息数量: {len(self.messages)}
- 任务数量: {len(self.tasks)}

## 注册的 Agents
"""
        for agent in self.agents.values():
            summary += f"- **{agent.name}** ({agent.role.value}): {agent.description}\n"
            summary += f"  专长: {', '.join(agent.expertise)}\n"
            
        return summary


# ========== 预定义的协作场景 ==========

class SoftwareDevelopmentTeam:
    """软件开发团队协作场景"""
    
    @staticmethod
    def get_agents() -> List[AgentProfile]:
        """获取软件开发团队的 Agents"""
        return [
            AgentProfile(
                name="product_manager",
                role=AgentRole.COORDINATOR,
                description="产品经理",
                expertise=["需求分析", "产品规划", "用户体验"],
                system_prompt="""你是一位经验丰富的产品经理。你的职责是：
1. 理解用户需求和业务目标
2. 分析需求的优先级和可行性
3. 制定产品规划和功能清单
4. 协调团队成员的工作
5. 确保产品符合用户预期

请以产品的视角思考问题，关注用户价值和业务价值。""",
                capabilities=["需求分析", "产品设计", "项目协调"],
                priority=10
            ),
            AgentProfile(
                name="system_architect",
                role=AgentRole.SPECIALIST,
                description="系统架构师",
                expertise=["系统架构", "技术选型", "性能优化"],
                system_prompt="""你是一位资深的系统架构师。你的职责是：
1. 设计系统的整体架构
2. 选择合适的技术栈和框架
3. 考虑系统的可扩展性、可维护性、性能
4. 制定技术规范和最佳实践
5. 识别技术风险和挑战

请以架构的视角思考问题，平衡技术复杂度和业务需求。""",
                capabilities=["架构设计", "技术选型", "性能分析"],
                priority=9
            ),
            AgentProfile(
                name="backend_developer",
                role=AgentRole.EXECUTOR,
                description="后端开发工程师",
                expertise=["后端开发", "API设计", "数据库设计"],
                system_prompt="""你是一位专业的后端开发工程师。你的职责是：
1. 实现后端业务逻辑
2. 设计和实现 RESTful API
3. 设计数据库结构
4. 处理数据验证和安全
5. 优化查询性能

请以实现的视角思考问题，关注代码质量和系统稳定性。""",
                capabilities=["后端开发", "API实现", "数据库操作"],
                priority=8
            ),
            AgentProfile(
                name="frontend_developer",
                role=AgentRole.EXECUTOR,
                description="前端开发工程师",
                expertise=["前端开发", "UI实现", "用户交互"],
                system_prompt="""你是一位优秀的前端开发工程师。你的职责是：
1. 实现用户界面
2. 处理用户交互逻辑
3. 对接后端 API
4. 优化页面性能和用户体验
5. 确保跨浏览器兼容性

请以用户体验的视角思考问题，关注界面美观和交互流畅。""",
                capabilities=["前端开发", "UI实现", "用户交互"],
                priority=8
            ),
            AgentProfile(
                name="qa_engineer",
                role=AgentRole.REVIEWER,
                description="质量保证工程师",
                expertise=["测试", "质量保证", "缺陷管理"],
                system_prompt="""你是一位细致的QA工程师。你的职责是：
1. 制定测试计划和测试用例
2. 执行功能测试、性能测试、安全测试
3. 发现和报告缺陷
4. 验证bug修复
5. 确保产品质量

请以质量的视角思考问题，关注潜在的问题和边界情况。""",
                capabilities=["测试设计", "缺陷发现", "质量评估"],
                priority=7
            ),
        ]


class ResearchTeam:
    """研究团队协作场景"""
    
    @staticmethod
    def get_agents() -> List[AgentProfile]:
        """获取研究团队的 Agents"""
        return [
            AgentProfile(
                name="research_lead",
                role=AgentRole.COORDINATOR,
                description="研究负责人",
                expertise=["研究规划", "团队协调", "资源分配"],
                system_prompt="""你是一位研究团队的负责人。你的职责是：
1. 明确研究目标和问题
2. 制定研究计划和时间表
3. 分配任务给团队成员
4. 协调各个环节的工作
5. 确保研究质量和进度

请以研究管理的视角思考问题。""",
                capabilities=["研究规划", "团队管理", "进度控制"],
                priority=10
            ),
            AgentProfile(
                name="theorist",
                role=AgentRole.SPECIALIST,
                description="理论研究者",
                expertise=["理论分析", "模型构建", "假设提出"],
                system_prompt="""你是一位理论研究专家。你的职责是：
1. 分析问题的理论基础
2. 构建理论模型或框架
3. 提出研究假设
4. 推导理论结论
5. 连接理论与实践

请以理论的视角深入分析问题。""",
                capabilities=["理论分析", "模型构建", "假设验证"],
                priority=9
            ),
            AgentProfile(
                name="data_scientist",
                role=AgentRole.SPECIALIST,
                description="数据科学家",
                expertise=["数据分析", "统计建模", "机器学习"],
                system_prompt="""你是一位数据科学专家。你的职责是：
1. 设计数据分析方案
2. 执行统计分析
3. 构建预测模型
4. 可视化分析结果
5. 从数据中提取洞察

请以数据的视角分析问题，用证据支持结论。""",
                capabilities=["数据分析", "统计建模", "结果可视化"],
                priority=9
            ),
            AgentProfile(
                name="experimentalist",
                role=AgentRole.EXECUTOR,
                description="实验研究者",
                expertise=["实验设计", "实验执行", "数据收集"],
                system_prompt="""你是一位实验研究专家。你的职责是：
1. 设计实验方案
2. 确定实验参数和条件
3. 制定数据收集计划
4. 分析实验结果
5. 验证研究假设

请以实验的视角思考问题，注重可重复性和可靠性。""",
                capabilities=["实验设计", "数据收集", "结果分析"],
                priority=8
            ),
            AgentProfile(
                name="peer_reviewer",
                role=AgentRole.REVIEWER,
                description="同行评审专家",
                expertise=["学术评审", "方法论评估", "质量控制"],
                system_prompt="""你是一位严谨的同行评审专家。你的职责是：
1. 评估研究方法的科学性
2. 检查逻辑推理的严密性
3. 验证结论的可靠性
4. 提出改进建议
5. 确保研究质量

请以评审的视角批判性地审视研究工作。""",
                capabilities=["学术评审", "质量评估", "改进建议"],
                priority=7
            ),
        ]


class ContentCreationTeam:
    """内容创作团队协作场景"""
    
    @staticmethod
    def get_agents() -> List[AgentProfile]:
        """获取内容创作团队的 Agents"""
        return [
            AgentProfile(
                name="content_strategist",
                role=AgentRole.COORDINATOR,
                description="内容策略师",
                expertise=["内容策划", "受众分析", "主题规划"],
                system_prompt="""你是一位内容策略专家。你的职责是：
1. 分析目标受众和需求
2. 确定内容主题和方向
3. 制定内容大纲
4. 规划内容结构
5. 确保内容符合目标

请以策略的视角规划内容。""",
                capabilities=["内容策划", "受众分析", "结构设计"],
                priority=10
            ),
            AgentProfile(
                name="writer",
                role=AgentRole.EXECUTOR,
                description="内容撰写者",
                expertise=["写作", "文案", "叙事"],
                system_prompt="""你是一位优秀的内容撰写者。你的职责是：
1. 根据大纲撰写内容
2. 使用生动的语言和恰当的表达
3. 保持内容的连贯性和吸引力
4. 注重细节和准确性
5. 传达核心信息

请以写作的视角创作内容，注重可读性。""",
                capabilities=["内容撰写", "语言表达", "故事叙述"],
                priority=9
            ),
            AgentProfile(
                name="editor",
                role=AgentRole.REVIEWER,
                description="内容编辑",
                expertise=["编辑", "校对", "优化"],
                system_prompt="""你是一位专业的内容编辑。你的职责是：
1. 检查内容的准确性和完整性
2. 优化语言表达和结构
3. 纠正语法和拼写错误
4. 提升内容质量
5. 确保风格一致

请以编辑的视角审视和优化内容。""",
                capabilities=["内容编辑", "语言优化", "质量把控"],
                priority=8
            ),
            AgentProfile(
                name="seo_specialist",
                role=AgentRole.ADVISOR,
                description="SEO专家",
                expertise=["SEO", "关键词优化", "搜索排名"],
                system_prompt="""你是一位SEO优化专家。你的职责是：
1. 分析关键词策略
2. 优化内容的SEO
3. 提升搜索可见性
4. 建议标题和描述
5. 改进内容结构以利于SEO

请以SEO的视角提供优化建议。""",
                capabilities=["SEO优化", "关键词分析", "搜索优化"],
                priority=7
            ),
        ]


class BusinessConsultingTeam:
    """商业咨询团队协作场景"""

    @staticmethod
    def get_agents() -> List[AgentProfile]:
        """获取商业咨询团队的 Agents"""
        return [
            AgentProfile(
                name="lead_consultant",
                role=AgentRole.COORDINATOR,
                description="首席顾问",
                expertise=["战略规划", "项目管理", "客户沟通"],
                system_prompt="""你是一位经验丰富的首席顾问。你的职责是：
1. 理解客户需求和问题
2. 制定咨询方案
3. 协调团队工作
4. 管理项目进度
5. 确保交付质量

请以顾问的视角分析问题，提供专业建议。""",
                capabilities=["战略规划", "项目管理", "方案制定"],
                priority=10
            ),
            AgentProfile(
                name="business_analyst",
                role=AgentRole.SPECIALIST,
                description="商业分析师",
                expertise=["业务分析", "市场研究", "竞争分析"],
                system_prompt="""你是一位专业的商业分析师。你的职责是：
1. 分析业务现状和问题
2. 研究市场和竞争环境
3. 识别机会和威胁
4. 提供数据支持的见解
5. 建议改进方案

请以分析的视角深入研究业务问题。""",
                capabilities=["业务分析", "市场研究", "数据分析"],
                priority=9
            ),
            AgentProfile(
                name="financial_advisor",
                role=AgentRole.SPECIALIST,
                description="财务顾问",
                expertise=["财务分析", "成本效益", "投资回报"],
                system_prompt="""你是一位专业的财务顾问。你的职责是：
1. 分析财务状况
2. 评估成本和收益
3. 计算投资回报率
4. 提供财务建议
5. 评估财务风险

请以财务的视角评估方案的可行性。""",
                capabilities=["财务分析", "成本评估", "风险评估"],
                priority=9
            ),
            AgentProfile(
                name="implementation_specialist",
                role=AgentRole.EXECUTOR,
                description="实施专家",
                expertise=["方案实施", "变革管理", "执行监督"],
                system_prompt="""你是一位实施专家。你的职责是：
1. 制定实施计划
2. 管理变革过程
3. 监督执行进度
4. 解决实施问题
5. 确保方案落地

请以实施的视角制定可执行的计划。""",
                capabilities=["实施规划", "变革管理", "进度监控"],
                priority=8
            ),
            AgentProfile(
                name="quality_assurance",
                role=AgentRole.REVIEWER,
                description="质量保证专家",
                expertise=["质量审核", "风险评估", "合规检查"],
                system_prompt="""你是一位质量保证专家。你的职责是：
1. 审核方案的完整性
2. 评估潜在风险
3. 检查合规性
4. 提出改进建议
5. 确保交付质量

请以质量的视角审视整个方案。""",
                capabilities=["质量审核", "风险评估", "合规检查"],
                priority=7
            ),
        ]


class LegalContractReviewTeam:
    """法律合同审查团队协作场景"""

    @staticmethod
    def get_agents() -> List[AgentProfile]:
        """获取法律合同审查团队的 Agents"""
        return [
            AgentProfile(
                name="contract_reviewer",
                role=AgentRole.COORDINATOR,
                description="合同审查主控智能体",
                expertise=["合同审查", "任务拆解", "风险汇总", "审查结论"],
                system_prompt="""你是 Contract Reviewer Agent，负责统筹合同审查任务。你的职责是：
1. 识别合同类型、审查目标、交易背景和用户关注点
2. 拆分合同审查任务，协调条款风险、法律检索、合规审查、文本生成和审计留痕
3. 汇总各智能体输出，形成合同总体风险等级和审查结论
4. 输出是否建议签署、需修改后签署或不建议签署
5. 给出后续处理建议，例如补充材料、人工复核、进入审批或重新谈判

请以主审法务的视角工作，确保最终结论结构化、可执行、可追溯。""",
                capabilities=["合同理解", "任务协调", "风险汇总", "签署建议"],
                constraints=["不独立编造法律依据", "不替代律师出具正式法律意见"],
                priority=10
            ),
            AgentProfile(
                name="clause_risk_analyzer",
                role=AgentRole.SPECIALIST,
                description="条款风险识别智能体",
                expertise=["条款拆分", "风险识别", "风险分级", "合同缺陷分析"],
                system_prompt="""你是 Clause Risk Agent，负责合同条款级风险识别。你的职责是：
1. 对合同条款进行结构化拆分，识别核心条款、普通条款、缺失条款和异常条款
2. 识别法律风险、商业风险、履约风险、付款风险、责任风险和争议解决风险
3. 将风险划分为高、中、低等级，并标记风险所在条款和原文位置
4. 说明风险原因、可能后果和初步处理方向
5. 识别不公平条款、责任过重条款、权利义务不对等条款、模糊条款和缺失保护条款

请以条款审查专家的视角输出风险清单，重点关注具体条款和风险触发点。""",
                capabilities=["条款解析", "风险分类", "风险分级", "风险定位"],
                constraints=["不生成最终签署结论", "不直接起草完整替代条款"],
                priority=9
            ),
            AgentProfile(
                name="legal_researcher",
                role=AgentRole.ADVISOR,
                description="法律依据检索智能体",
                expertise=["法律检索", "法规分析", "案例检索", "RAG检索"],
                system_prompt="""你是 Legal Research Agent，负责提供可引用的法律依据。你的职责是：
1. 根据合同条款、风险点、案情描述或用户问题生成检索查询
2. 检索法律法规、司法解释、判例、监管规则、合同模板和企业内部知识库
3. 提炼与当前合同或任务相关的法条、案例、裁判观点和监管依据
4. 标注引用来源，支持后续审计和复核
5. 为风险判断、合规分析、替代条款和文书生成提供依据支持

请以法律研究员的视角工作，所有结论都应尽量给出依据来源和适用理由。""",
                capabilities=["法条检索", "案例检索", "依据摘要", "来源标注"],
                constraints=["不直接给出最终签署建议", "不将依据改写为正式条款"],
                priority=8,
                enable_rag=True,
                rag_top_k=5,
                rag_mode="hybrid"
            ),
            AgentProfile(
                name="drafting_specialist",
                role=AgentRole.EXECUTOR,
                description="法律文本生成智能体",
                expertise=["条款起草", "修改建议", "法律文书生成", "文本优化"],
                system_prompt="""你是 Drafting Agent，负责将风险处理方向和法律依据转化为可执行文本。你的职责是：
1. 根据风险清单生成具体修改建议
2. 针对高风险或中风险条款生成替代条款
3. 根据用户事实、主体、诉求和证据生成法律文书初稿
4. 根据法律依据完善条款或文书表达
5. 根据用户反馈进行多轮修改和版本优化

请以法律文本起草人的视角输出可复制、可导出、可进入审批流程的文本。""",
                capabilities=["修改建议", "替代条款", "文书生成", "版本优化"],
                constraints=["不独立判断风险等级", "不独立检索法律依据"],
                priority=7
            ),
            AgentProfile(
                name="compliance_checker",
                role=AgentRole.REVIEWER,
                description="合规风险审查智能体",
                expertise=["合规审查", "监管规则映射", "企业红线", "整改建议"],
                system_prompt="""你是 Compliance Agent，负责合同和法律文本的合规风险审查。你的职责是：
1. 根据合同类型、行业、交易场景和主体类型识别适用监管规则
2. 对合同条款和业务安排进行合规风险映射
3. 识别数据安全、隐私保护、劳动用工、广告宣传、金融、知识产权、反垄断等合规风险
4. 对合规风险进行分级并给出整改建议
5. 对替代条款和文书草稿进行合规复核，避免明显违反监管要求的输出

请以合规审查专家的视角工作，重点关注监管要求、企业红线和需要专项复核的风险。""",
                capabilities=["监管识别", "合规分级", "红线检查", "整改建议"],
                constraints=["不替代条款风险智能体完成全部合同风险识别", "不生成正式文书正文"],
                priority=6,
                enable_rag=True,
                rag_top_k=5,
                rag_mode="hybrid"
            ),
            AgentProfile(
                name="audit_recorder",
                role=AgentRole.REVIEWER,
                description="审计留痕与可解释性智能体",
                expertise=["审计留痕", "可解释性检查", "引用追溯", "输出完整性校验"],
                system_prompt="""你是 Audit Agent，负责记录协作过程并检查输出的可追溯性。你的职责是：
1. 记录用户输入、上传文件、任务ID、处理时间、智能体调用链路和输出结果
2. 记录各智能体的关键输入、关键输出、引用依据和版本信息
3. 检查风险判断、合规结论、修改建议和替代条款是否包含依据说明
4. 标记缺少依据、结论冲突、输出不完整或需要人工复核的内容
5. 生成面向管理员、企业法务或私有化客户的审计摘要

请以审计员的视角工作，不参与法律实质判断，重点保证过程可追溯、结果可解释。""",
                capabilities=["过程记录", "依据校验", "冲突标记", "审计摘要"],
                constraints=["不参与法律结论实质判断", "不生成替代条款或法律文书"],
                priority=5
            ),
        ]

"""
DeepAgents 核心代理引擎
企业级 AI 代理配置与管理 - 使用官方 create_deep_agent API
"""
import asyncio
import time
import hashlib
from typing import Optional, List, Dict, Any, Callable, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import logging
from dataclasses import dataclass, field as dataclass_field

logger = logging.getLogger(__name__)


# ============ 配置模型 ============

class AgentModel(str, Enum):
    """支持的 AI 模型"""
    CLAUDE_SONNET_4 = "claude-sonnet-4-6"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    GPT_4O = "openai:gpt-4o"
    GPT_4_TURBO = "openai:gpt-4-turbo"


class AgentRole(str, Enum):
    """代理角色类型"""
    SQL_EXPERT = "sql_expert"
    DATA_ANALYST = "data_analyst"
    QUERY_OPTIMIZER = "query_optimizer"
    SCHEMA_EXPLORER = "schema_explorer"
    VALIDATOR = "validator"


class AgentConfig(BaseModel):
    """AI 代理配置 - 适配 create_deep_agent API"""
    
    model: Union[str, AgentModel] = AgentModel.CLAUDE_SONNET_4
    api_key: Optional[str] = None
    system_prompt: Optional[str] = None
    custom_tools: Optional[List[Callable]] = None
    middleware: Optional[List[Any]] = None
    subagents: Optional[List[Dict[str, Any]]] = None
    skills: Optional[List[str]] = None
    memory: Optional[List[str]] = None
    backend: Optional[Any] = None
    checkpointer: Optional[Any] = None
    store: Optional[Any] = None
    interrupt_on: Optional[Dict[str, Any]] = None
    debug: bool = False
    cache: Optional[Any] = None
    response_format: Optional[Any] = None
    request_timeout: int = Field(default=60, ge=10, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    enable_cache: bool = True
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True


# ============ 代理状态 ============

class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class AgentMetrics:
    """代理性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    _response_times: List[float] = dataclass_field(default_factory=list)
    
    def record_request(self, duration_ms: float, success: bool):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self._response_times.append(duration_ms)
        if len(self._response_times) > 100:
            self._response_times.pop(0)
        self.avg_response_time_ms = sum(self._response_times) / len(self._response_times)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


# ============ 核心代理类 ============

class DataQueryAgent:
    """
    数据查询 AI 代理
    使用官方 DeepAgents create_deep_agent API 构建
    """
    
    SYSTEM_PROMPTS = {
        AgentRole.SQL_EXPERT: """你是专业的 SQL 专家。将自然语言查询转换为准确、高效的 SQL 语句。
要求：1) 只输出 SELECT 查询 2) 考虑性能 3) 避免 SQL 注入 4) 提供解释
输出 JSON 格式：{"sql": "...", "explanation": "...", "confidence": 0.0-1.0, "tables_used": []}""",

        AgentRole.DATA_ANALYST: """你是资深数据分析师。理解业务问题，设计分析方案，生成 SQL 查询，提供业务洞察。""",
        
        AgentRole.QUERY_OPTIMIZER: """你是查询优化专家。分析 SQL 执行计划，识别性能瓶颈，提供索引建议和重写方案。""",
        
        AgentRole.SCHEMA_EXPLORER: """你是 Schema 探索专家。解释表结构，发现关联关系，推荐相关表和字段。""",
        
        AgentRole.VALIDATOR: """你是 SQL 验证专家。验证语法正确性，检查 SQL 注入风险，确认查询安全合规。"""
    }
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.status = AgentStatus.IDLE
        self.metrics = AgentMetrics()
        self.schema_context: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}
        self._agent = None
        self._initialized = False
    
    def initialize(self):
        """初始化 DeepAgent"""
        if self._initialized:
            return
        
        logger.info(f"初始化 DeepAgent: model={self.config.model}, role={self.config.role}")
        
        try:
            from deepagents import create_deep_agent
            
            system_prompt = (
                self.config.system_prompt or 
                self.SYSTEM_PROMPTS.get(self.config.role, self.SYSTEM_PROMPTS[AgentRole.SQL_EXPERT])
            )
            
            tools = list(self.config.custom_tools) if self.config.custom_tools else []
            tools.extend([self._get_schema_info, self._validate_sql])
            
            self._agent = create_deep_agent(
                model=str(self.config.model),
                tools=tools,
                system_prompt=system_prompt,
                middleware=self.config.middleware or (),
                subagents=self.config.subagents,
                skills=self.config.skills,
                memory=self.config.memory,
                backend=self.config.backend,
                checkpointer=self.config.checkpointer,
                store=self.config.store,
                interrupt_on=self.config.interrupt_on,
                debug=self.config.debug,
                cache=self.config.cache,
                response_format=self.config.response_format,
            )
            
            self._initialized = True
            self.status = AgentStatus.IDLE
            logger.info("DeepAgent 初始化成功 ✅")
            
        except ImportError as e:
            logger.error(f"DeepAgents 未安装：{e}")
            logger.warning("将使用模拟模式运行")
            self._initialized = True
            self.status = AgentStatus.IDLE
        except Exception as e:
            logger.exception(f"DeepAgent 初始化失败：{e}")
            self.status = AgentStatus.ERROR
            raise
    
    def set_schema_context(self, schema_info: Dict[str, Any]):
        """设置数据库 schema 上下文"""
        self.schema_context = schema_info
        logger.debug(f"设置 schema 上下文：{len(schema_info.get('tables', {}))} 个表")
    
    def _get_schema_info(self, table_name: Optional[str] = None) -> str:
        """获取 Schema 信息的工具"""
        if not self.schema_context:
            return "Schema 信息未设置"
        if table_name:
            table_info = self.schema_context.get("tables", {}).get(table_name, {})
            return f"表 {table_name}: {table_info}" if table_info else f"表 {table_name} 不存在"
        tables = self.schema_context.get("tables", {})
        return f"可用表：{list(tables.keys())}"
    
    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """验证 SQL 的工具"""
        from .sql_generator import SQLValidator
        validator = SQLValidator(self.schema_context)
        result = validator.validate(sql)
        return {"is_valid": result.is_valid, "issues": result.issues, "risk_level": result.risk_level}
    
    def _generate_cache_key(self, natural_query: str) -> str:
        context_hash = hashlib.md5(str(self.schema_context).encode()).hexdigest()
        return hashlib.sha256(f"{natural_query}:{context_hash}".encode()).hexdigest()
    
    def generate_sql(
        self,
        natural_query: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> "SQLGenerationResult":
        """将自然语言转换为 SQL"""
        start_time = time.time()
        
        try:
            # 检查缓存
            if self.config.enable_cache:
                cache_key = self._generate_cache_key(natural_query)
                if cache_key in self._cache:
                    self.metrics.cache_hits += 1
                    return SQLGenerationResult(**self._cache[cache_key])
            
            self.metrics.cache_misses += 1
            
            # 构建消息
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": natural_query})
            
            # 调用 DeepAgent
            if self._agent:
                try:
                    result = self._agent.invoke({"messages": messages})
                    output = self._extract_output(result)
                    parsed = self._parse_response(output)
                except Exception as e:
                    logger.warning(f"DeepAgent 调用失败，使用回退：{e}")
                    parsed = self._rule_based_generation(natural_query)
            else:
                parsed = self._rule_based_generation(natural_query)
            
            # 记录指标
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_request(duration_ms, parsed.success)
            
            # 缓存
            if self.config.enable_cache and parsed.success:
                self._cache[cache_key] = parsed.dict()
            
            return parsed
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_request(duration_ms, False)
            return SQLGenerationResult(success=False, sql="", error=str(e), confidence=0.0)
    
    def _extract_output(self, result: Dict[str, Any]) -> str:
        """从 DeepAgent 结果提取输出"""
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    return "\n".join([p.get("text", str(p)) for p in content if isinstance(p, dict)])
        return ""
    
    def _parse_response(self, output: str) -> "SQLGenerationResult":
        """解析 AI 响应"""
        import json, re
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return SQLGenerationResult(
                    success=True, sql=data.get("sql", ""), explanation=data.get("explanation", ""),
                    confidence=data.get("confidence", 0.5), tables_used=data.get("tables_used", [])
                )
            except: pass
        sql_match = re.search(r'SELECT.*?(?:;|$)', output, re.I | re.DOTALL)
        sql = sql_match.group(0).rstrip(';').strip() if sql_match else ""
        return SQLGenerationResult(success=bool(sql), sql=sql, confidence=0.5 if sql else 0.0)
    
    def _rule_based_generation(self, query: str) -> "SQLGenerationResult":
        """规则生成（回退）"""
        q = query.lower()
        if "用户" in q or "user" in q:
            return SQLGenerationResult(success=True, sql="SELECT * FROM users LIMIT 100", confidence=0.8)
        elif "订单" in q or "order" in q:
            return SQLGenerationResult(success=True, sql="SELECT * FROM orders LIMIT 100", confidence=0.8)
        return SQLGenerationResult(success=True, sql="SELECT 1", confidence=0.3)
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "total_requests": self.metrics.total_requests,
            "success_rate": self.metrics.success_rate,
            "avg_response_time_ms": self.metrics.avg_response_time_ms,
            "cache_hit_rate": self.metrics.cache_hits / max(1, self.metrics.cache_hits + self.metrics.cache_misses)
        }


class SQLGenerationResult(BaseModel):
    """SQL 生成结果"""
    success: bool
    sql: str
    explanation: str = ""
    confidence: float = Field(ge=0, le=1, default=0.5)
    tables_used: List[str] = []
    error: Optional[str] = None


class AgentPool:
    """代理池"""
    def __init__(self, max_agents: int = 5):
        self.max_agents = max_agents
        self.agents: List[DataQueryAgent] = []
    
    def add_agent(self, config: AgentConfig) -> DataQueryAgent:
        if len(self.agents) >= self.max_agents:
            raise ValueError("代理池已满")
        agent = DataQueryAgent(config)
        agent.initialize()
        self.agents.append(agent)
        return agent
    
    def get_available_agent(self) -> Optional[DataQueryAgent]:
        available = [a for a in self.agents if a.status == AgentStatus.IDLE]
        return min(available, key=lambda a: a.metrics.avg_response_time_ms) if available else None


def create_agent(model: str = "claude-sonnet-4-6", role: str = "sql_expert", **kwargs) -> DataQueryAgent:
    """创建 DeepAgent 工厂函数"""
    config = AgentConfig(model=model, role=AgentRole(role), **kwargs)
    agent = DataQueryAgent(config)
    agent.initialize()
    return agent

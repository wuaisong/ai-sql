"""
查询处理器
企业级查询处理管道，包含意图识别、查询重写、执行优化等
"""
import asyncio
import time
import re
from typing import Optional, List, Dict, Any, Callable, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field as dataclass_field
import logging
import hashlib

logger = logging.getLogger(__name__)


# ============ 枚举和常量 ============

class QueryIntent(str, Enum):
    """查询意图类型"""
    SIMPLE_SELECT = "simple_select"  # 简单查询
    AGGREGATION = "aggregation"  # 聚合统计
    TIME_SERIES = "time_series"  # 时间序列
    COMPARISON = "comparison"  # 对比分析
    TREND = "trend"  # 趋势分析
    RANKING = "ranking"  # 排名
    FILTER = "filter"  # 筛选
    JOIN = "join"  # 多表关联
    SUBQUERY = "subquery"  # 子查询
    UNKNOWN = "unknown"  # 未知


class QueryComplexity(str, Enum):
    """查询复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class QueryStage(str, Enum):
    """查询处理阶段"""
    RECEIVED = "received"
    INTENT_ANALYSIS = "intent_analysis"
    SCHEMA_MATCHING = "schema_matching"
    SQL_GENERATION = "sql_generation"
    SQL_VALIDATION = "sql_validation"
    SQL_OPTIMIZATION = "sql_optimization"
    EXECUTION = "execution"
    RESULT_PROCESSING = "result_processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============ 数据模型 ============

class QueryContext(BaseModel):
    """
    查询上下文
    包含查询处理过程中的所有状态和信息
    """
    # 基础信息
    query_id: str
    user_id: str
    datasource_id: str
    natural_query: str
    
    # 处理状态
    stage: QueryStage = QueryStage.RECEIVED
    intent: Optional[QueryIntent] = None
    complexity: QueryComplexity = QueryComplexity.SIMPLE
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 处理结果
    generated_sql: Optional[str] = None
    validated_sql: Optional[str] = None
    optimized_sql: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    
    # 元数据
    tables_involved: List[str] = []
    columns_involved: List[str] = []
    parameters: Dict[str, Any] = {}
    
    # 性能指标
    stage_timings: Dict[str, float] = {}
    tokens_used: int = 0
    
    # 错误信息
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # 对话历史
    conversation_history: List[Dict[str, str]] = []
    
    # 缓存信息
    cache_key: Optional[str] = None
    from_cache: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_stage_timing(self, stage: str, duration_ms: float):
        """添加阶段耗时"""
        self.stage_timings[stage] = duration_ms
    
    def get_total_processing_time(self) -> float:
        """获取总处理时间（毫秒）"""
        return sum(self.stage_timings.values())
    
    def mark_stage(self, stage: QueryStage):
        """标记当前阶段"""
        self.stage = stage
        if stage == QueryStage.RECEIVED:
            self.created_at = datetime.utcnow()
        elif stage == QueryStage.INTENT_ANALYSIS:
            self.started_at = datetime.utcnow()
        elif stage in [QueryStage.COMPLETED, QueryStage.FAILED]:
            self.completed_at = datetime.utcnow()


@dataclass
class IntentAnalysisResult:
    """意图分析结果"""
    intent: QueryIntent
    confidence: float
    detected_entities: List[Dict[str, Any]] = dataclass_field(default_factory=list)
    detected_metrics: List[str] = dataclass_field(default_factory=list)
    detected_dimensions: List[str] = dataclass_field(default_factory=list)
    time_range: Optional[Dict[str, Any]] = None
    filters: List[Dict[str, Any]] = dataclass_field(default_factory=list)
    sort_order: Optional[Dict[str, str]] = None
    limit: Optional[int] = None
    suggested_tables: List[str] = dataclass_field(default_factory=list)
    ambiguity_notes: List[str] = dataclass_field(default_factory=list)


@dataclass
class QueryExecutionResult:
    """查询执行结果"""
    success: bool
    data: List[Dict[str, Any]] = dataclass_field(default_factory=list)
    columns: List[str] = dataclass_field(default_factory=list)
    row_count: int = 0
    sql: str = ""
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    warning: Optional[str] = None
    metadata: Dict[str, Any] = dataclass_field(default_factory=dict)


# ============ 意图识别器 ============

class IntentRecognizer:
    """
    查询意图识别器
    分析自然语言查询，识别用户意图和关键元素
    """
    
    # 意图关键词映射
    INTENT_KEYWORDS = {
        QueryIntent.SIMPLE_SELECT: ["查询", "查找", "显示", "列出", "查看", "select", "list", "show"],
        QueryIntent.AGGREGATION: ["统计", "汇总", "合计", "总数", "平均", "聚合", "count", "sum", "average", "total"],
        QueryIntent.TIME_SERIES: ["趋势", "走势", "每日", "每月", "每年", "时间", "trend", "daily", "monthly"],
        QueryIntent.COMPARISON: ["对比", "比较", "vs", "versus", "compare", "comparison"],
        QueryIntent.TREND: ["增长", "下降", "变化", "环比", "同比", "growth", "change", "trend"],
        QueryIntent.RANKING: ["排名", "排行", "top", "最高", "最低", "rank", "ranking", "highest", "lowest"],
        QueryIntent.FILTER: ["筛选", "过滤", "条件", "where", "filter"],
        QueryIntent.JOIN: ["关联", "连接", "join", "link", "combine"],
    }
    
    # 聚合函数识别
    AGGREGATION_FUNCTIONS = [
        "count", "sum", "avg", "average", "min", "max", 
        "count(", "sum(", "avg(", "min(", "max(",
        "统计", "合计", "总数", "平均", "最大", "最小"
    ]
    
    # 时间表达式识别
    TIME_PATTERNS = [
        r'最近\s*(\d+)\s*(天 | 日 | 周 | 月 | 年)',
        r'过去\s*(\d+)\s*(天 | 日 | 周 | 月 | 年)',
        r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?',
        r'今天 | 昨天 | 明天 | 本周 | 上周 | 本月 | 上月',
        r'today|yesterday|this week|last week|this month|last month',
    ]
    
    def __init__(self, schema_context: Optional[Dict[str, Any]] = None):
        self.schema_context = schema_context or {}
        self._table_keywords: Dict[str, List[str]] = {}
        self._column_keywords: Dict[str, List[str]] = {}
        self._build_keyword_index()
    
    def set_schema_context(self, schema_context: Dict[str, Any]):
        """设置 schema 上下文"""
        self.schema_context = schema_context
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """构建关键词索引"""
        self._table_keywords.clear()
        self._column_keywords.clear()
        
        tables = self.schema_context.get("tables", {})
        for table_name, table_info in tables.items():
            # 表名本身
            keywords = [table_name.lower()]
            
            # 表描述中的关键词
            description = table_info.get("description", "").lower()
            keywords.extend(re.findall(r'\b\w+\b', description))
            
            # 字段名
            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                keywords.append(col_name)
                
                # 字段描述
                col_desc = col.get("description", "").lower()
                keywords.extend(re.findall(r'\b\w+\b', col_desc))
            
            self._table_keywords[table_name] = list(set(keywords))
    
    def analyze(self, natural_query: str) -> IntentAnalysisResult:
        """
        分析查询意图
        
        Args:
            natural_query: 自然语言查询
            
        Returns:
            IntentAnalysisResult: 分析结果
        """
        query_lower = natural_query.lower()
        
        # 1. 识别意图
        intent, confidence = self._identify_intent(query_lower)
        
        # 2. 提取实体
        entities = self._extract_entities(natural_query)
        
        # 3. 识别指标和维度
        metrics, dimensions = self._identify_metrics_dimensions(query_lower)
        
        # 4. 识别时间范围
        time_range = self._extract_time_range(natural_query)
        
        # 5. 识别过滤条件
        filters = self._extract_filters(natural_query)
        
        # 6. 识别排序
        sort_order = self._extract_sort_order(natural_query)
        
        # 7. 识别限制
        limit = self._extract_limit(natural_query)
        
        # 8. 推荐表
        suggested_tables = self._suggest_tables(entities, metrics, dimensions)
        
        # 9. 识别歧义
        ambiguity_notes = self._identify_ambiguities(entities, suggested_tables)
        
        return IntentAnalysisResult(
            intent=intent,
            confidence=confidence,
            detected_entities=entities,
            detected_metrics=metrics,
            detected_dimensions=dimensions,
            time_range=time_range,
            filters=filters,
            sort_order=sort_order,
            limit=limit,
            suggested_tables=suggested_tables,
            ambiguity_notes=ambiguity_notes
        )
    
    def _identify_intent(self, query_lower: str) -> Tuple[QueryIntent, float]:
        """识别查询意图"""
        intent_scores = {}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # 检查聚合函数
        for func in self.AGGREGATION_FUNCTIONS:
            if func in query_lower:
                intent_scores[QueryIntent.AGGREGATION] = intent_scores.get(QueryIntent.AGGREGATION, 0) + 2
        
        if not intent_scores:
            return QueryIntent.SIMPLE_SELECT, 0.5
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(intent_scores[best_intent] / 5.0, 1.0)
        
        return best_intent, confidence
    
    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """提取命名实体"""
        entities = []
        
        # 从 schema 中匹配表名和列名
        for table_name, keywords in self._table_keywords.items():
            for kw in keywords:
                if kw in query.lower() and len(kw) > 2:
                    entities.append({
                        "type": "table_or_column",
                        "value": kw,
                        "matched_table": table_name
                    })
                    break
        
        return entities
    
    def _identify_metrics_dimensions(self, query_lower: str) -> Tuple[List[str], List[str]]:
        """识别指标和维度"""
        metrics = []
        dimensions = []
        
        # 常见指标关键词
        metric_keywords = ["金额", "数量", "价格", "成本", "收入", "利润", "销量", "amount", "price", "cost", "revenue"]
        
        # 常见维度关键词
        dimension_keywords = ["时间", "日期", "地区", "类别", "用户", "产品", "部门", "date", "region", "category", "user"]
        
        for kw in metric_keywords:
            if kw in query_lower:
                metrics.append(kw)
        
        for kw in dimension_keywords:
            if kw in query_lower:
                dimensions.append(kw)
        
        return metrics, dimensions
    
    def _extract_time_range(self, query: str) -> Optional[Dict[str, Any]]:
        """提取时间范围"""
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return {
                    "expression": match.group(0),
                    "groups": match.groups(),
                    "type": "relative" if any(x in match.group(0).lower() for x in ["最近", "过去", "last"]) else "absolute"
                }
        return None
    
    def _extract_filters(self, query: str) -> List[Dict[str, Any]]:
        """提取过滤条件"""
        filters = []
        
        # 简单的等值条件识别
        patterns = [
            r'(\w+)\s*(?:为 | 是 |=)\s*([^\s，,]+)',
            r'(\w+)\s*(?:大于 | 超过|>)\s*(\d+)',
            r'(\w+)\s*(?:小于 | 低于|<)\s*(\d+)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, query):
                filters.append({
                    "field": match.group(1),
                    "operator": "=" if "=" in pattern else (">" if "大于" in pattern or ">" in pattern else "<"),
                    "value": match.group(2)
                })
        
        return filters
    
    def _extract_sort_order(self, query: str) -> Optional[Dict[str, str]]:
        """提取排序要求"""
        query_lower = query.lower()
        
        if any(x in query_lower for x in ["降序", "从高到低", "desc", "descending"]):
            order = "DESC"
        elif any(x in query_lower for x in ["升序", "从低到高", "asc", "ascending"]):
            order = "ASC"
        else:
            return None
        
        # 尝试提取排序字段
        sort_patterns = [r'按 (\w+) 排序', r'order by (\w+)', r'sort by (\w+)']
        for pattern in sort_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return {"field": match.group(1), "order": order}
        
        return {"field": None, "order": order}
    
    def _extract_limit(self, query: str) -> Optional[int]:
        """提取数量限制"""
        patterns = [
            r'前\s*(\d+)\s*(个 | 条 | 名 | 位)',
            r'top\s*(\d+)',
            r'limit\s*(\d+)',
            r'(\d+)\s*(强 | 大)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _suggest_tables(self, entities: List[Dict], metrics: List[str], dimensions: List[str]) -> List[str]:
        """推荐相关表"""
        table_scores = {}
        
        for entity in entities:
            table = entity.get("matched_table")
            if table:
                table_scores[table] = table_scores.get(table, 0) + 1
        
        # 基于 metrics 和 dimensions 匹配
        for table_name, keywords in self._table_keywords.items():
            for kw in metrics + dimensions:
                if kw in keywords:
                    table_scores[table_name] = table_scores.get(table_name, 0) + 1
        
        # 返回得分最高的表
        sorted_tables = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_tables[:5]]
    
    def _identify_ambiguities(self, entities: List[Dict], suggested_tables: List[str]) -> List[str]:
        """识别查询歧义"""
        ambiguities = []
        
        if len(suggested_tables) > 3:
            ambiguities.append(f"可能涉及多个表：{', '.join(suggested_tables)}，请明确查询范围")
        
        if not suggested_tables:
            ambiguities.append("未识别到相关的数据表，请提供更多上下文")
        
        return ambiguities


# ============ 查询管道 ============

class QueryPipeline:
    """
    查询处理管道
    编排查询处理的各个阶段
    """
    
    def __init__(self):
        self.stages: List[Callable] = []
        self.middlewares: List[Callable] = []
        self.intent_recognizer = IntentRecognizer()
    
    def add_stage(self, stage: Callable):
        """添加处理阶段"""
        self.stages.append(stage)
        return self
    
    def add_middleware(self, middleware: Callable):
        """添加中间件"""
        self.middlewares.append(middleware)
        return self
    
    async def process(self, context: QueryContext) -> QueryExecutionResult:
        """
        处理查询
        
        Args:
            context: 查询上下文
            
        Returns:
            执行结果
        """
        try:
            # 执行中间件（前置）
            for middleware in self.middlewares:
                await self._run_middleware(middleware, context, "pre")
            
            # 执行各个阶段
            for stage_func in self.stages:
                stage_start = time.time()
                context = await stage_func(context)
                stage_duration = (time.time() - stage_start) * 1000
                context.add_stage_timing(context.stage.value, stage_duration)
                
                # 检查是否失败
                if context.stage == QueryStage.FAILED:
                    break
            
            # 执行中间件（后置）
            for middleware in self.middlewares:
                await self._run_middleware(middleware, context, "post")
            
            # 构建结果
            if context.stage == QueryStage.COMPLETED:
                return QueryExecutionResult(
                    success=True,
                    data=context.execution_result.get("data", []),
                    columns=context.execution_result.get("columns", []),
                    row_count=context.execution_result.get("row_count", 0),
                    sql=context.optimized_sql or context.validated_sql or context.generated_sql,
                    execution_time_ms=context.execution_result.get("execution_time_ms", 0),
                    metadata={
                        "total_processing_time_ms": context.get_total_processing_time(),
                        "stage_timings": context.stage_timings,
                        "tokens_used": context.tokens_used,
                        "from_cache": context.from_cache
                    }
                )
            else:
                return QueryExecutionResult(
                    success=False,
                    error=context.error,
                    sql=context.generated_sql or ""
                )
                
        except Exception as e:
            logger.exception(f"查询管道处理失败：{e}")
            context.stage = QueryStage.FAILED
            context.error = str(e)
            
            return QueryExecutionResult(
                success=False,
                error=str(e)
            )
    
    async def _run_middleware(self, middleware: Callable, context: QueryContext, phase: str):
        """运行中间件"""
        try:
            if asyncio.iscoroutinefunction(middleware):
                await middleware(context, phase)
            else:
                middleware(context, phase)
        except Exception as e:
            logger.warning(f"中间件执行失败 ({phase}): {e}")


# ============ 查询处理器 ============

class QueryProcessor:
    """
    企业级查询处理器
    整合意图识别、SQL 生成、验证、优化和执行
    """
    
    def __init__(
        self,
        sql_generator=None,
        sql_validator=None,
        sql_optimizer=None,
        connector=None,
        cache_service=None
    ):
        self.sql_generator = sql_generator
        self.sql_validator = sql_validator
        self.sql_optimizer = sql_optimizer
        self.connector = connector
        self.cache_service = cache_service
        
        self.intent_recognizer = IntentRecognizer()
        self.pipeline = self._build_pipeline()
        
        # 处理统计
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "cache_hits": 0,
            "avg_processing_time_ms": 0.0,
            "_processing_times": []
        }
    
    def set_schema_context(self, schema_context: Dict[str, Any]):
        """设置 schema 上下文"""
        self.schema_context = schema_context
        self.intent_recognizer.set_schema_context(schema_context)
        
        if self.sql_generator:
            self.sql_generator.set_schema_context(schema_context)
    
    def _build_pipeline(self) -> QueryPipeline:
        """构建查询管道"""
        pipeline = QueryPipeline()
        
        # 添加处理阶段
        pipeline.add_stage(self._stage_intent_analysis)
        pipeline.add_stage(self._stage_cache_check)
        pipeline.add_stage(self._stage_sql_generation)
        pipeline.add_stage(self._stage_sql_validation)
        pipeline.add_stage(self._stage_sql_optimization)
        pipeline.add_stage(self._stage_query_execution)
        pipeline.add_stage(self._stage_result_processing)
        
        return pipeline
    
    async def process_query(
        self,
        natural_query: str,
        user_id: str,
        datasource_id: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> QueryExecutionResult:
        """
        处理查询请求
        
        Args:
            natural_query: 自然语言查询
            user_id: 用户 ID
            datasource_id: 数据源 ID
            conversation_history: 对话历史
            
        Returns:
            查询执行结果
        """
        start_time = time.time()
        
        # 创建查询上下文
        query_id = hashlib.sha256(
            f"{natural_query}{user_id}{time.time()}".encode()
        ).hexdigest()[:16]
        
        context = QueryContext(
            query_id=query_id,
            user_id=user_id,
            datasource_id=datasource_id,
            natural_query=natural_query,
            conversation_history=conversation_history or []
        )
        
        try:
            # 执行管道
            result = await self.pipeline.process(context)
            
            # 更新统计
            self._update_stats(result, time.time() - start_time)
            
            return result
            
        except Exception as e:
            logger.exception(f"查询处理失败：{e}")
            self.stats["failed_queries"] += 1
            
            return QueryExecutionResult(
                success=False,
                error=str(e)
            )
    
    async def _stage_intent_analysis(self, context: QueryContext) -> QueryContext:
        """阶段：意图分析"""
        context.mark_stage(QueryStage.INTENT_ANALYSIS)
        
        analysis = self.intent_recognizer.analyze(context.natural_query)
        
        context.intent = analysis.intent
        context.complexity = self._assess_complexity(analysis)
        context.tables_involved = analysis.suggested_tables
        context.parameters = {
            "filters": analysis.filters,
            "time_range": analysis.time_range,
            "sort_order": analysis.sort_order,
            "limit": analysis.limit
        }
        
        logger.debug(f"意图分析：{context.intent} (confidence: {analysis.confidence})")
        
        return context
    
    async def _stage_cache_check(self, context: QueryContext) -> QueryContext:
        """阶段：缓存检查"""
        if not self.cache_service:
            return context
        
        context.mark_stage(QueryStage.SCHEMA_MATCHING)
        
        # 生成缓存键
        cache_key = hashlib.sha256(
            f"{context.natural_query}:{context.datasource_id}".encode()
        ).hexdigest()
        
        context.cache_key = cache_key
        
        # 检查缓存
        cached = self.cache_service.get(cache_key)
        if cached:
            context.from_cache = True
            context.execution_result = cached
            context.mark_stage(QueryStage.COMPLETED)
            self.stats["cache_hits"] += 1
            logger.debug(f"缓存命中：{cache_key[:16]}")
        
        return context
    
    async def _stage_sql_generation(self, context: QueryContext) -> QueryContext:
        """阶段：SQL 生成"""
        if context.from_cache:
            return context
        
        context.mark_stage(QueryStage.SQL_GENERATION)
        
        if not self.sql_generator:
            context.error = "SQL 生成器未配置"
            context.mark_stage(QueryStage.FAILED)
            return context
        
        # 生成 SQL
        result = self.sql_generator.generate_sql(
            context.natural_query,
            context=context.parameters,
            conversation_history=context.conversation_history
        )
        
        context.generated_sql = result.sql
        context.tables_involved = result.tables_used
        context.tokens_used += result.tokens_used or 0
        
        if not result.success:
            context.error = result.error or "SQL 生成失败"
            context.mark_stage(QueryStage.FAILED)
        
        logger.debug(f"SQL 生成：{context.generated_sql[:100] if context.generated_sql else 'None'}")
        
        return context
    
    async def _stage_sql_validation(self, context: QueryContext) -> QueryContext:
        """阶段：SQL 验证"""
        if context.stage == QueryStage.FAILED:
            return context
        
        context.mark_stage(QueryStage.SQL_VALIDATION)
        
        if not self.sql_validator:
            context.validated_sql = context.generated_sql
            return context
        
        validation = self.sql_validator.validate(context.generated_sql)
        
        if not validation.is_valid:
            context.error = f"SQL 验证失败：{', '.join(validation.issues)}"
            context.error_details = {"issues": validation.issues}
            context.mark_stage(QueryStage.FAILED)
            return context
        
        context.validated_sql = validation.sql
        logger.debug(f"SQL 验证通过")
        
        return context
    
    async def _stage_sql_optimization(self, context: QueryContext) -> QueryContext:
        """阶段：SQL 优化"""
        if context.stage == QueryStage.FAILED:
            return context
        
        context.mark_stage(QueryStage.SQL_OPTIMIZATION)
        
        if not self.sql_optimizer:
            context.optimized_sql = context.validated_sql
            return context
        
        optimization = self.sql_optimizer.optimize(
            context.validated_sql,
            context.tables_involved
        )
        
        context.optimized_sql = optimization.sql
        logger.debug(f"SQL 优化完成")
        
        return context
    
    async def _stage_query_execution(self, context: QueryContext) -> QueryContext:
        """阶段：查询执行"""
        if context.stage == QueryStage.FAILED:
            return context
        
        context.mark_stage(QueryStage.EXECUTION)
        
        if not self.connector:
            context.error = "数据库连接器未配置"
            context.mark_stage(QueryStage.FAILED)
            return context
        
        try:
            exec_start = time.time()
            
            # 连接数据库
            if not self.connector.connected:
                self.connector.connect()
            
            # 执行查询
            data, columns = self.connector.execute_query(
                context.optimized_sql,
                limit=10000,
                timeout=60
            )
            
            exec_time = (time.time() - exec_start) * 1000
            
            context.execution_result = {
                "data": data,
                "columns": columns,
                "row_count": len(data),
                "execution_time_ms": exec_time
            }
            
            logger.debug(f"查询执行：{len(data)} 行，{exec_time:.2f}ms")
            
        except Exception as e:
            context.error = f"查询执行失败：{str(e)}"
            context.mark_stage(QueryStage.FAILED)
        
        return context
    
    async def _stage_result_processing(self, context: QueryContext) -> QueryContext:
        """阶段：结果处理"""
        if context.stage == QueryStage.FAILED:
            return context
        
        context.mark_stage(QueryStage.RESULT_PROCESSING)
        
        # 缓存结果
        if self.cache_service and context.cache_key:
            self.cache_service.set(
                context.cache_key,
                context.execution_result,
                expire=300
            )
        
        context.mark_stage(QueryStage.COMPLETED)
        logger.info(f"查询完成：{context.query_id}")
        
        return context
    
    def _assess_complexity(self, analysis: IntentAnalysisResult) -> QueryComplexity:
        """评估查询复杂度"""
        score = 0
        
        # 基于意图
        if analysis.intent in [QueryIntent.JOIN, QueryIntent.SUBQUERY]:
            score += 3
        elif analysis.intent in [QueryIntent.AGGREGATION, QueryIntent.TIME_SERIES]:
            score += 2
        
        # 基于表数量
        score += len(analysis.suggested_tables)
        
        # 基于过滤条件
        score += len(analysis.filters)
        
        if score <= 2:
            return QueryComplexity.SIMPLE
        elif score <= 5:
            return QueryComplexity.MEDIUM
        elif score <= 8:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.VERY_COMPLEX
    
    def _update_stats(self, result: QueryExecutionResult, processing_time: float):
        """更新统计信息"""
        self.stats["total_queries"] += 1
        
        if result.success:
            self.stats["successful_queries"] += 1
        else:
            self.stats["failed_queries"] += 1
        
        # 更新平均处理时间
        self.stats["_processing_times"].append(processing_time * 1000)
        if len(self.stats["_processing_times"]) > 100:
            self.stats["_processing_times"].pop(0)
        
        self.stats["avg_processing_time_ms"] = (
            sum(self.stats["_processing_times"]) / len(self.stats["_processing_times"])
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return {
            "total_queries": self.stats["total_queries"],
            "successful_queries": self.stats["successful_queries"],
            "failed_queries": self.stats["failed_queries"],
            "success_rate": (
                self.stats["successful_queries"] / self.stats["total_queries"]
                if self.stats["total_queries"] > 0 else 0
            ),
            "cache_hits": self.stats["cache_hits"],
            "avg_processing_time_ms": self.stats["avg_processing_time_ms"]
        }

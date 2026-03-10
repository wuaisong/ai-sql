"""
SQL 生成器、验证器和优化器
企业级 SQL 处理核心组件
"""
import re
import hashlib
from typing import Optional, List, Dict, Any, Tuple, Set
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field as dataclass_field
import logging

logger = logging.getLogger(__name__)


# ============ 结果模型 ============

class SQLGenerationResult(BaseModel):
    """SQL 生成结果"""
    success: bool
    sql: str
    explanation: str = ""
    confidence: float = Field(ge=0, le=1, default=0.5)
    tables_used: List[str] = []
    columns_used: List[str] = []
    potential_issues: List[str] = []
    optimization_suggestions: List[str] = []
    error: Optional[str] = None
    tokens_used: Optional[int] = None


class SQLValidationResult(BaseModel):
    """SQL 验证结果"""
    is_valid: bool
    sql: str
    issues: List[str] = []
    warnings: List[str] = []
    is_readonly: bool = True
    risk_level: str = "low"  # low, medium, high, critical
    detected_operations: List[str] = []


class SQLOptimizationResult(BaseModel):
    """SQL 优化结果"""
    original_sql: str
    optimized_sql: str
    improvements: List[str] = []
    estimated_performance_gain: str = ""
    index_suggestions: List[str] = []
    rewrite_suggestions: List[str] = []


# ============ SQL 生成器 ============

class SQLGenerator:
    """
    SQL 生成器
    基于 AI 和规则混合的方式生成 SQL
    """
    
    # SQL 模板库
    SQL_TEMPLATES = {
        "simple_select": "SELECT {columns} FROM {table}{where}{order}{limit}",
        "aggregation": "SELECT {dimensions}, {aggregations} FROM {table}{where}{group_by}{order}{limit}",
        "time_series": "SELECT {time_column}, {aggregations} FROM {table}{where}{group_by}{order}",
        "ranking": "SELECT {columns} FROM {table}{where}{order}{limit}",
        "join": "SELECT {columns} FROM {table1} {join_type} {table2} ON {join_condition}{where}{order}{limit}",
        "comparison": """
SELECT 
    {dimension},
    SUM(CASE WHEN {condition1} THEN {metric} ELSE 0 END) AS {label1},
    SUM(CASE WHEN {condition2} THEN {metric} ELSE 0 END) AS {label2}
FROM {table}
{where}
GROUP BY {dimension}
{order}
""",
        "trend": """
SELECT 
    {time_column},
    {aggregation} AS current_value,
    LAG({aggregation}) OVER (ORDER BY {time_column}) AS previous_value,
    ROUND(
        ({aggregation} - LAG({aggregation}) OVER (ORDER BY {time_column})) * 100.0 / 
        NULLIF(LAG({aggregation}) OVER (ORDER BY {time_column}), 0), 
        2
    ) AS change_percent
FROM {table}
{where}
GROUP BY {time_column}
ORDER BY {time_column}
"""
    }
    
    # 聚合函数映射
    AGGREGATION_MAP = {
        "count": "COUNT(*)",
        "sum": "SUM({column})",
        "avg": "AVG({column})",
        "average": "AVG({column})",
        "min": "MIN({column})",
        "max": "MAX({column})",
        "distinct": "COUNT(DISTINCT {column})"
    }
    
    # 时间粒度映射
    TIME_GRANULARITY = {
        "day": "DATE({column})",
        "daily": "DATE({column})",
        "week": "DATE_TRUNC('week', {column})",
        "weekly": "DATE_TRUNC('week', {column})",
        "month": "DATE_TRUNC('month', {column})",
        "monthly": "DATE_TRUNC('month', {column})",
        "year": "DATE_TRUNC('year', {column})",
        "yearly": "DATE_TRUNC('year', {column})",
        "hour": "DATE_TRUNC('hour', {column})"
    }
    
    def __init__(self, ai_agent=None):
        """
        初始化 SQL 生成器
        
        Args:
            ai_agent: AI 代理（用于复杂查询生成）
        """
        self.ai_agent = ai_agent
        self.schema_context: Dict[str, Any] = {}
        self._table_cache: Dict[str, Dict] = {}
    
    def set_schema_context(self, schema_info: Dict[str, Any]):
        """设置数据库 schema 上下文"""
        self.schema_context = schema_info
        self._table_cache = schema_info.get("tables", {})
    
    def generate_sql(
        self,
        natural_query: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> SQLGenerationResult:
        """
        生成 SQL
        
        Args:
            natural_query: 自然语言查询
            context: 查询上下文（意图、实体等）
            conversation_history: 对话历史
            
        Returns:
            SQLGenerationResult
        """
        try:
            # 优先使用 AI 生成（如果有配置）
            if self.ai_agent:
                ai_result = self.ai_agent.generate_sql(natural_query, context)
                if ai_result.get("success"):
                    return SQLGenerationResult(
                        success=True,
                        sql=ai_result.get("sql", ""),
                        explanation=ai_result.get("explanation", ""),
                        confidence=ai_result.get("confidence", 0.5),
                        tables_used=ai_result.get("tables_used", []),
                        potential_issues=ai_result.get("potential_issues", []),
                        optimization_suggestions=ai_result.get("optimization_suggestions", [])
                    )
            
            # 回退到规则生成
            return self._rule_based_generation(natural_query, context)
            
        except Exception as e:
            logger.exception(f"SQL 生成失败：{e}")
            return SQLGenerationResult(
                success=False,
                sql="",
                error=str(e),
                confidence=0.0
            )
    
    def _rule_based_generation(
        self,
        natural_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SQLGenerationResult:
        """基于规则的 SQL 生成"""
        query_lower = natural_query.lower()
        context = context or {}
        
        # 1. 确定查询类型
        query_type = self._determine_query_type(query_lower, context)
        
        # 2. 选择模板
        template = self.SQL_TEMPLATES.get(query_type, self.SQL_TEMPLATES["simple_select"])
        
        # 3. 提取和映射元素
        tables = context.get("suggested_tables", [])
        if not tables:
            tables = self._match_tables(query_lower)
        
        columns = self._select_columns(query_lower, tables)
        where_clause = self._build_where_clause(context.get("filters", []))
        order_clause = self._build_order_clause(context.get("sort_order", {}), columns)
        limit_clause = self._build_limit_clause(context.get("limit"))
        
        # 4. 填充模板
        sql_params = {
            "columns": columns.get("select", "*"),
            "table": tables[0] if tables else "unknown_table",
            "table1": tables[0] if len(tables) > 0 else "unknown_table",
            "table2": tables[1] if len(tables) > 1 else "unknown_table",
            "where": where_clause,
            "order": order_clause,
            "limit": limit_clause,
            "dimensions": columns.get("dimensions", ""),
            "aggregations": columns.get("aggregations", "COUNT(*)"),
            "group_by": columns.get("group_by", ""),
            "join_type": "JOIN",
            "join_condition": self._infer_join_condition(tables),
            "time_column": columns.get("time_column", "created_at"),
            "metric": columns.get("metric", "amount"),
            "condition1": context.get("condition1", "1=1"),
            "condition2": context.get("condition2", "1=2"),
            "label1": "group_1",
            "label2": "group_2"
        }
        
        sql = template.format(**sql_params).strip()
        
        # 5. 后处理
        sql = self._post_process_sql(sql)
        
        return SQLGenerationResult(
            success=True,
            sql=sql,
            explanation=f"基于规则生成的 {query_type} 查询",
            confidence=0.6,
            tables_used=tables,
            columns_used=columns.get("all", []),
            potential_issues=self._check_potential_issues(sql, tables),
            optimization_suggestions=self._generate_optimization_suggestions(sql)
        )
    
    def _determine_query_type(self, query_lower: str, context: Dict) -> str:
        """确定查询类型"""
        # 从上下文获取意图
        intent = context.get("intent")
        if intent:
            intent_str = str(intent).lower()
            if "aggregat" in intent_str:
                return "aggregation"
            elif "time" in intent_str or "trend" in intent_str:
                return "time_series"
            elif "rank" in intent_str:
                return "ranking"
            elif "compar" in intent_str:
                return "comparison"
        
        # 基于关键词判断
        if any(kw in query_lower for kw in ["统计", "汇总", "合计", "总数", "平均"]):
            return "aggregation"
        elif any(kw in query_lower for kw in ["趋势", "走势", "每日", "每月"]):
            return "time_series"
        elif any(kw in query_lower for kw in ["排名", "排行", "top", "最高"]):
            return "ranking"
        elif any(kw in query_lower for kw in ["对比", "比较", "vs"]):
            return "comparison"
        elif any(kw in query_lower for kw in ["关联", "连接"]):
            return "join"
        
        return "simple_select"
    
    def _match_tables(self, query_lower: str) -> List[str]:
        """匹配相关表"""
        matched = []
        
        for table_name, table_info in self._table_cache.items():
            # 检查表名
            if table_name.lower() in query_lower:
                matched.append(table_name)
                continue
            
            # 检查表描述
            description = table_info.get("description", "").lower()
            if any(kw in description for kw in query_lower.split()):
                matched.append(table_name)
                continue
            
            # 检查字段
            for col in table_info.get("columns", []):
                if col.get("name", "").lower() in query_lower:
                    matched.append(table_name)
                    break
        
        return list(set(matched))[:5]
    
    def _select_columns(
        self,
        query_lower: str,
        tables: List[str]
    ) -> Dict[str, Any]:
        """选择列"""
        if not tables:
            return {"select": "*", "all": []}
        
        # 获取第一个表的列
        table_info = self._table_cache.get(tables[0], {})
        columns = table_info.get("columns", [])
        
        # 默认选择所有列
        select_columns = ["*"]
        all_columns = [col.get("name") for col in columns]
        
        # 尝试匹配查询中提到的列
        mentioned_cols = []
        for col in columns:
            col_name = col.get("name", "").lower()
            if col_name in query_lower:
                mentioned_cols.append(col.get("name"))
        
        if mentioned_cols:
            select_columns = mentioned_cols
        
        # 检查聚合需求
        aggregations = []
        dimensions = []
        
        if any(kw in query_lower for kw in ["统计", "合计", "总数"]):
            # 查找数值列
            for col in columns:
                col_type = col.get("type", "").upper()
                if any(t in col_type for t in ["INT", "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE"]):
                    aggregations.append(f"SUM({col.get('name')}) AS total_{col.get('name')}")
                    break
        
        if any(kw in query_lower for kw in ["平均"]):
            for col in columns:
                col_type = col.get("type", "").upper()
                if any(t in col_type for t in ["INT", "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE"]):
                    aggregations.append(f"AVG({col.get('name')}) AS avg_{col.get('name')}")
                    break
        
        # 时间列
        time_column = "created_at"
        for col in columns:
            col_name = col.get("name", "").lower()
            if any(t in col_name for t in ["date", "time", "created", "updated"]):
                time_column = col.get("name")
                break
        
        return {
            "select": ", ".join(select_columns) if select_columns != ["*"] else "*",
            "all": all_columns,
            "aggregations": ", ".join(aggregations) if aggregations else "COUNT(*)",
            "dimensions": ", ".join(dimensions) if dimensions else "",
            "group_by": f"GROUP BY {', '.join(dimensions)}" if dimensions else "",
            "time_column": time_column,
            "metric": columns[0].get("name") if columns else "id"
        }
    
    def _build_where_clause(self, filters: List[Dict]) -> str:
        """构建 WHERE 子句"""
        if not filters:
            return ""
        
        conditions = []
        for f in filters:
            field = f.get("field", "")
            operator = f.get("operator", "=")
            value = f.get("value", "")
            
            # 值处理
            if isinstance(value, str) and not value.isdigit():
                value = f"'{value}'"
            
            conditions.append(f"{field} {operator} {value}")
        
        if not conditions:
            return ""
        
        return " WHERE " + " AND ".join(conditions)
    
    def _build_order_clause(self, sort_order: Optional[Dict], columns: List[str]) -> str:
        """构建 ORDER BY 子句"""
        if not sort_order:
            return ""
        
        field = sort_order.get("field")
        order = sort_order.get("order", "DESC")
        
        if not field:
            # 默认按第一个数值列排序
            return " ORDER BY created_at DESC"
        
        return f" ORDER BY {field} {order}"
    
    def _build_limit_clause(self, limit: Optional[int]) -> str:
        """构建 LIMIT 子句"""
        if not limit:
            return " LIMIT 100"
        
        return f" LIMIT {min(limit, 10000)}"
    
    def _infer_join_condition(self, tables: List[str]) -> str:
        """推断连接条件"""
        if len(tables) < 2:
            return "1=1"
        
        # 简单的启发式：假设外键命名 convention
        table1, table2 = tables[0], tables[1]
        
        # 尝试常见的外键模式
        return f"{table2}.id = {table1}.{table2.rstrip('s')}_id"
    
    def _post_process_sql(self, sql: str) -> str:
        """后处理 SQL"""
        # 清理多余空格
        sql = re.sub(r'\s+', ' ', sql)
        
        # 清理模板残留
        sql = sql.replace("{", "").replace("}", "")
        
        # 确保以分号结尾（可选）
        # sql = sql.rstrip(';')
        
        return sql.strip()
    
    def _check_potential_issues(self, sql: str, tables: List[str]) -> List[str]:
        """检查潜在问题"""
        issues = []
        
        # 检查 SELECT *
        if "SELECT *" in sql.upper():
            issues.append("使用 SELECT * 可能影响性能，建议明确指定列")
        
        # 检查缺少 WHERE
        if "WHERE" not in sql.upper() and "SELECT" in sql.upper():
            issues.append("查询缺少 WHERE 条件，可能返回大量数据")
        
        # 检查缺少 LIMIT
        if "LIMIT" not in sql.upper() and "SELECT" in sql.upper():
            issues.append("查询缺少 LIMIT，建议添加行数限制")
        
        # 检查表是否存在
        for table in tables:
            if table not in self._table_cache:
                issues.append(f"表 '{table}' 未在 schema 中找到，请确认表名")
        
        return issues
    
    def _generate_optimization_suggestions(self, sql: str) -> List[str]:
        """生成优化建议"""
        suggestions = []
        sql_upper = sql.upper()
        
        # 检查索引使用
        if "WHERE" in sql_upper:
            suggestions.append("确保 WHERE 条件中的列有适当的索引")
        
        # 检查 JOIN
        if "JOIN" in sql_upper:
            suggestions.append("检查 JOIN 条件列是否有索引")
        
        # 检查聚合
        if "GROUP BY" in sql_upper:
            suggestions.append("GROUP BY 列建议添加索引以提升性能")
        
        return suggestions


# ============ SQL 验证器 ============

class SQLValidator:
    """
    SQL 验证器
    验证 SQL 的安全性、正确性和合规性
    """
    
    # 危险操作列表
    DANGEROUS_OPERATIONS = {
        "critical": ["DROP", "TRUNCATE", "DELETE", "ALTER", "CREATE", "GRANT", "REVOKE"],
        "high": ["INSERT", "UPDATE", "REPLACE", "MERGE"],
        "medium": ["LOCK", "UNLOCK", "SET"],
        "low": ["SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN"]
    }
    
    # SQL 注入模式
    INJECTION_PATTERNS = [
        r"--\s*$",  # SQL 注释
        r"/\*.*\*/",  # 块注释
        r";\s*(?:DROP|DELETE|UPDATE|INSERT)",  # 分号后的危险操作
        r"'\s*OR\s*'1'\s*=\s*'1",  # OR 注入
        r"'\s*OR\s+1\s*=\s*1",  # OR 注入变体
        r"UNION\s+(?:ALL\s+)?SELECT",  # UNION 注入
        r"EXEC\s*\(",  # 执行存储过程
        r"xp_cmdshell",  # SQL Server 命令执行
    ]
    
    def __init__(self, schema_context: Optional[Dict[str, Any]] = None):
        self.schema_context = schema_context or {}
        self._table_cache = self.schema_context.get("tables", {})
    
    def set_schema_context(self, schema_info: Dict[str, Any]):
        """设置 schema 上下文"""
        self.schema_context = schema_info
        self._table_cache = schema_info.get("tables", {})
    
    def validate(self, sql: str) -> SQLValidationResult:
        """
        验证 SQL
        
        Args:
            sql: SQL 语句
            
        Returns:
            SQLValidationResult
        """
        if not sql or not sql.strip():
            return SQLValidationResult(
                is_valid=False,
                sql=sql,
                issues=["SQL 语句为空"],
                risk_level="critical"
            )
        
        sql = sql.strip()
        sql_upper = sql.upper()
        issues = []
        warnings = []
        detected_ops = []
        
        # 1. 检查危险操作
        risk_level = "low"
        for level, operations in self.DANGEROUS_OPERATIONS.items():
            for op in operations:
                if re.search(r'\b' + op + r'\b', sql_upper):
                    detected_ops.append(op)
                    if level == "critical":
                        risk_level = "critical"
                        issues.append(f"检测到危险操作：{op}")
                    elif level == "high" and risk_level != "critical":
                        risk_level = "high"
                        issues.append(f"检测到数据修改操作：{op}")
        
        # 2. 检查 SQL 注入
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                issues.append(f"检测到潜在的 SQL 注入模式")
                risk_level = "critical"
        
        # 3. 检查只读性
        is_readonly = sql_upper.startswith("SELECT") or sql_upper.startswith("WITH") or sql_upper.startswith("EXPLAIN")
        
        # 4. 验证表名
        if self._table_cache:
            mentioned_tables = self._extract_tables(sql)
            for table in mentioned_tables:
                if table not in self._table_cache:
                    warnings.append(f"表 '{table}' 未在 schema 中找到")
        
        # 5. 检查复杂度警告
        join_count = sql_upper.count("JOIN")
        if join_count > 5:
            warnings.append(f"查询包含 {join_count} 个 JOIN，可能影响性能")
        
        if sql_upper.count("SUBQUERY") > 3 or sql_upper.count("(SELECT") > 3:
            warnings.append("查询包含多个子查询，建议优化")
        
        # 6. 检查资源消耗
        if "CROSS JOIN" in sql_upper:
            warnings.append("CROSS JOIN 可能导致大量数据，请谨慎使用")
        
        is_valid = len(issues) == 0 and risk_level not in ["critical", "high"]
        
        return SQLValidationResult(
            is_valid=is_valid,
            sql=sql,
            issues=issues,
            warnings=warnings,
            is_readonly=is_readonly,
            risk_level=risk_level,
            detected_operations=detected_ops
        )
    
    def _extract_tables(self, sql: str) -> Set[str]:
        """提取 SQL 中提到的表名"""
        tables = set()
        
        # 简单的表名提取
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, sql, re.IGNORECASE):
                tables.add(match.group(1))
        
        return tables
    
    def validate_batch(self, sql_statements: List[str]) -> List[SQLValidationResult]:
        """批量验证 SQL"""
        return [self.validate(sql) for sql in sql_statements]


# ============ SQL 优化器 ============

class SQLOptimizer:
    """
    SQL 优化器
    优化 SQL 查询性能
    """
    
    def __init__(self, schema_context: Optional[Dict[str, Any]] = None):
        self.schema_context = schema_context or {}
        self._table_cache = self.schema_context.get("tables", {})
        self._index_cache: Dict[str, List[str]] = {}
    
    def set_schema_context(self, schema_info: Dict[str, Any]):
        """设置 schema 上下文"""
        self.schema_context = schema_info
        self._table_cache = schema_info.get("tables", {})
    
    def optimize(self, sql: str, tables: Optional[List[str]] = None) -> SQLOptimizationResult:
        """
        优化 SQL
        
        Args:
            sql: 原始 SQL
            tables: 涉及的表
            
        Returns:
            SQLOptimizationResult
        """
        if not sql:
            return SQLOptimizationResult(
                original_sql=sql,
                optimized_sql=sql
            )
        
        optimized = sql
        improvements = []
        index_suggestions = []
        rewrite_suggestions = []
        
        # 1. 格式化优化
        optimized = self._format_sql(optimized)
        
        # 2. SELECT * 优化
        if "SELECT *" in optimized.upper():
            rewrite_suggestions.append("建议将 SELECT * 替换为明确的列名")
        
        # 3. 检查 WHERE 条件
        where_cols = self._extract_where_columns(optimized)
        for col in where_cols:
            index_suggestions.append(f"建议在 {col} 列上添加索引")
        
        # 4. JOIN 优化
        if "JOIN" in optimized.upper():
            join_conditions = self._extract_join_conditions(optimized)
            for condition in join_conditions:
                index_suggestions.append(f"建议在 JOIN 条件列上添加索引：{condition}")
        
        # 5. 子查询优化
        if self._has_correlated_subquery(optimized):
            rewrite_suggestions.append("检测到相关子查询，建议改写为 JOIN")
        
        # 6. DISTINCT 优化
        if "DISTINCT" in optimized.upper() and "GROUP BY" not in optimized.upper():
            rewrite_suggestions.append("考虑使用 GROUP BY 替代 DISTINCT")
        
        # 7. OR 条件优化
        if self._has_inefficient_or(optimized):
            rewrite_suggestions.append("多个 OR 条件可考虑使用 UNION 或 IN")
        
        # 8. 添加/优化 LIMIT
        if "LIMIT" not in optimized.upper() and optimized.upper().startswith("SELECT"):
            optimized = optimized.rstrip(";").rstrip() + " LIMIT 10000"
            improvements.append("添加 LIMIT 限制返回行数")
        
        # 9. 检查 N+1 查询模式
        if self._detect_n_plus_one(optimized):
            rewrite_suggestions.append("检测到可能的 N+1 查询模式，建议使用批量查询")
        
        # 估计性能提升
        estimated_gain = self._estimate_performance_gain(improvements, index_suggestions)
        
        return SQLOptimizationResult(
            original_sql=sql,
            optimized_sql=optimized,
            improvements=improvements,
            estimated_performance_gain=estimated_gain,
            index_suggestions=index_suggestions,
            rewrite_suggestions=rewrite_suggestions
        )
    
    def _format_sql(self, sql: str) -> str:
        """格式化 SQL"""
        # 清理多余空格
        sql = re.sub(r'\s+', ' ', sql)
        sql = sql.strip()
        return sql
    
    def _extract_where_columns(self, sql: str) -> List[str]:
        """提取 WHERE 条件中的列"""
        columns = []
        
        where_match = re.search(r'WHERE\s+(.+?)(?:GROUP|ORDER|LIMIT|$)', sql, re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1)
            # 提取列名
            col_matches = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>]', where_clause)
            columns.extend(col_matches)
        
        return list(set(columns))
    
    def _extract_join_conditions(self, sql: str) -> List[str]:
        """提取 JOIN 条件"""
        conditions = []
        
        for match in re.finditer(r'ON\s+([^\s]+)\s*=\s*([^\s]+)', sql, re.IGNORECASE):
            conditions.append(f"{match.group(1)} = {match.group(2)}")
        
        return conditions
    
    def _has_correlated_subquery(self, sql: str) -> bool:
        """检查是否有相关子查询"""
        # 简化检测：子查询中包含外部表的引用
        subquery_matches = re.findall(r'\(SELECT[^)]+\)', sql, re.IGNORECASE)
        for subquery in subquery_matches:
            # 检查是否引用了外部列（简化：检查是否有表别名.列名）
            if re.search(r'[a-z]+\.[a-z]+', subquery, re.IGNORECASE):
                return True
        return False
    
    def _has_inefficient_or(self, sql: str) -> bool:
        """检查低效的 OR 条件"""
        or_count = len(re.findall(r'\bOR\b', sql, re.IGNORECASE))
        return or_count >= 3
    
    def _detect_n_plus_one(self, sql: str) -> bool:
        """检测 N+1 查询模式"""
        # 简化检测：SELECT 中包含子查询且子查询引用外部表
        if re.search(r'SELECT.*\(SELECT.*FROM.*WHERE.*=.*\.', sql, re.IGNORECASE):
            return True
        return False
    
    def _estimate_performance_gain(
        self,
        improvements: List[str],
        index_suggestions: List[str]
    ) -> str:
        """估计性能提升"""
        score = 0
        
        score += len(improvements) * 10
        score += len(index_suggestions) * 20
        
        if score == 0:
            return "无明显优化空间"
        elif score < 30:
            return "预计提升 10-30%"
        elif score < 60:
            return "预计提升 30-50%"
        else:
            return "预计提升 50% 以上"
    
    def suggest_indexes(
        self,
        sql: str,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """
        为给定 SQL 建议索引
        
        Args:
            sql: SQL 语句
            table_name: 表名
            
        Returns:
            索引建议列表
        """
        suggestions = []
        
        # WHERE 列
        where_cols = self._extract_where_columns(sql)
        for col in where_cols:
            suggestions.append({
                "type": "index",
                "table": table_name,
                "columns": [col],
                "reason": "WHERE 条件列",
                "priority": "high"
            })
        
        # ORDER BY 列
        order_match = re.search(r'ORDER\s+BY\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        if order_match:
            suggestions.append({
                "type": "index",
                "table": table_name,
                "columns": [order_match.group(1)],
                "reason": "ORDER BY 列",
                "priority": "medium"
            })
        
        # GROUP BY 列
        group_match = re.search(r'GROUP\s+BY\s+(.+?)(?:ORDER|LIMIT|$)', sql, re.IGNORECASE)
        if group_match:
            group_cols = [c.strip() for c in group_match.group(1).split(',')]
            suggestions.append({
                "type": "index",
                "table": table_name,
                "columns": group_cols,
                "reason": "GROUP BY 列",
                "priority": "high"
            })
        
        return suggestions


# ============ 工厂函数 ============

def create_sql_processor(
    schema_context: Optional[Dict[str, Any]] = None,
    ai_agent=None
) -> Tuple[SQLGenerator, SQLValidator, SQLOptimizer]:
    """
    创建 SQL 处理组件
    
    Args:
        schema_context: Schema 上下文
        ai_agent: AI 代理
        
    Returns:
        (SQLGenerator, SQLValidator, SQLOptimizer)
    """
    generator = SQLGenerator(ai_agent=ai_agent)
    validator = SQLValidator(schema_context=schema_context)
    optimizer = SQLOptimizer(schema_context=schema_context)
    
    if schema_context:
        generator.set_schema_context(schema_context)
        validator.set_schema_context(schema_context)
        optimizer.set_schema_context(schema_context)
    
    return generator, validator, optimizer

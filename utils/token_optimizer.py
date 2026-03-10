"""
Token 优化器
优化大模型 token 使用，防止超出上下文限制和消耗过多 token
"""
import tiktoken
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelContext(str, Enum):
    """模型上下文限制"""
    GPT_3_5_TURBO = "gpt-3.5-turbo"  # 16K
    GPT_4 = "gpt-4"  # 8K
    GPT_4_TURBO = "gpt-4-turbo"  # 128K
    GPT_4O = "gpt-4o"  # 128K
    CLAUDE_3_HAIKU = "claude-3-haiku"  # 200K
    CLAUDE_3_SONNET = "claude-3-sonnet"  # 200K
    CLAUDE_3_OPUS = "claude-3-opus"  # 200K


# 模型上下文限制（token）
MODEL_LIMITS = {
    ModelContext.GPT_3_5_TURBO: 16385,
    ModelContext.GPT_4: 8192,
    ModelContext.GPT_4_TURBO: 128000,
    ModelContext.GPT_4O: 128000,
    ModelContext.CLAUDE_3_HAIKU: 200000,
    ModelContext.CLAUDE_3_SONNET: 200000,
    ModelContext.CLAUDE_3_OPUS: 200000,
}

# 安全缓冲（保留一部分 token 给响应）
SAFETY_BUFFER = 0.2  # 保留 20%


@dataclass
class TokenUsage:
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class SchemaOptimizer:
    """
    Schema 优化器
    优化发送给大模型的 schema 信息，减少 token 消耗
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.tokenizer = self._get_tokenizer(model)
        self.context_limit = MODEL_LIMITS.get(ModelContext(model), 128000)
        self.max_tokens = int(self.context_limit * (1 - SAFETY_BUFFER))
    
    def _get_tokenizer(self, model: str):
        """获取 tokenizer"""
        try:
            if "gpt" in model.lower():
                return tiktoken.encoding_for_model(model)
            elif "claude" in model.lower():
                return tiktoken.get_encoding("cl100k_base")
        except:
            pass
        # 回退到默认
        try:
            return tiktoken.get_encoding("cl100k_base")
        except:
            return None
    
    def count_tokens(self, text: str) -> int:
        """计算 token 数"""
        if not self.tokenizer:
            # 估算：4 字符 ≈ 1 token
            return len(text) // 4
        return len(self.tokenizer.encode(text))
    
    def optimize_schema(
        self,
        schema_info: Dict[str, Any],
        query: Optional[str] = None,
        max_tables: int = 20,
        max_columns_per_table: int = 15
    ) -> Tuple[Dict[str, Any], TokenUsage]:
        """
        优化 schema 信息
        
        Args:
            schema_info: 完整 schema
            query: 用户查询（用于智能选择相关表）
            max_tables: 最大表数量
            max_columns_per_table: 每表最大列数
            
        Returns:
            (优化后的 schema, token 使用统计)
        """
        usage = TokenUsage()
        
        if not schema_info:
            return {}, usage
        
        # 1. 选择相关表
        tables = schema_info.get("tables", {})
        
        if query:
            # 基于查询智能选择相关表
            selected_tables = self._select_relevant_tables(
                query, tables, max_tables
            )
        else:
            # 否则选择前 N 个表
            selected_tables = list(tables.keys())[:max_tables]
        
        # 2. 优化每个表的信息
        optimized_tables = {}
        schema_text = ""
        
        for table_name in selected_tables:
            if len(optimized_tables) >= max_tables:
                break
            
            table_info = tables.get(table_name, {})
            optimized_table = self._optimize_table_info(
                table_name, table_info, max_columns_per_table
            )
            optimized_tables[table_name] = optimized_table
            
            # 构建文本并计算 token
            table_text = self._format_table_for_prompt(table_name, optimized_table)
            schema_text += table_text
        
        # 3. 计算 token
        usage.prompt_tokens = self.count_tokens(schema_text)
        usage.total_tokens = usage.prompt_tokens
        
        # 4. 如果超出限制，进一步压缩
        if usage.prompt_tokens > self.max_tokens:
            logger.warning(f"Schema token 超出限制 ({usage.prompt_tokens} > {self.max_tokens})")
            optimized_tables, usage = self._aggressive_compress(
                optimized_tables, query
            )
        
        # 5. 估算成本
        usage.estimated_cost_usd = self._estimate_cost(usage)
        
        return {"tables": optimized_tables}, usage
    
    def _select_relevant_tables(
        self,
        query: str,
        tables: Dict[str, Any],
        max_tables: int
    ) -> List[str]:
        """基于查询选择相关表"""
        query_lower = query.lower()
        scored_tables = []
        
        for table_name, table_info in tables.items():
            score = 0
            
            # 表名匹配
            if table_name.lower() in query_lower:
                score += 10
            
            # 表描述匹配
            description = table_info.get("description", "").lower()
            if any(kw in description for kw in query_lower.split()):
                score += 5
            
            # 字段名匹配
            for col in table_info.get("columns", []):
                col_name = col.get("name", "").lower()
                if col_name in query_lower:
                    score += 3
            
            scored_tables.append((table_name, score))
        
        # 按分数排序
        scored_tables.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 N 个
        return [t[0] for t in scored_tables[:max_tables]]
    
    def _optimize_table_info(
        self,
        table_name: str,
        table_info: Dict[str, Any],
        max_columns: int
    ) -> Dict[str, Any]:
        """优化表信息"""
        optimized = {
            "description": table_info.get("description", "")[:100],  # 限制描述长度
        }
        
        # 选择重要列
        columns = table_info.get("columns", [])
        
        # 优先保留：主键、外键、常用字段
        priority_columns = []
        normal_columns = []
        
        for col in columns:
            col_name = col.get("name", "").lower()
            
            # 高优先级
            if any(kw in col_name for kw in ["id", "pk", "key", "code"]):
                priority_columns.append(col)
            # 中等优先级
            elif any(kw in col_name for kw in ["name", "type", "status", "date", "time", "amount"]):
                normal_columns.append(col)
            else:
                normal_columns.append(col)
        
        # 合并并限制数量
        selected_columns = (priority_columns + normal_columns)[:max_columns]
        
        # 优化列信息
        optimized["columns"] = []
        for col in selected_columns:
            optimized["columns"].append({
                "name": col.get("name"),
                "type": col.get("type", "")[:20],  # 限制类型长度
                "description": col.get("description", "")[:50] if col.get("description") else None
            })
        
        # 移除空字段
        optimized["columns"] = [
            {k: v for k, v in col.items() if v}
            for col in optimized["columns"]
        ]
        
        return optimized
    
    def _format_table_for_prompt(
        self,
        table_name: str,
        table_info: Dict[str, Any]
    ) -> str:
        """格式化表信息为 prompt 文本"""
        lines = [f"表：{table_name}"]
        
        if table_info.get("description"):
            lines.append(f"描述：{table_info['description']}")
        
        if table_info.get("columns"):
            lines.append("字段:")
            for col in table_info["columns"]:
                col_line = f"  - {col['name']} ({col.get('type', '')})"
                if col.get("description"):
                    col_line += f" - {col['description']}"
                lines.append(col_line)
        
        return "\n".join(lines) + "\n\n"
    
    def _aggressive_compress(
        self,
        tables: Dict[str, Any],
        query: Optional[str]
    ) -> Tuple[Dict[str, Any], TokenUsage]:
        """激进压缩"""
        usage = TokenUsage()
        
        # 只保留表名和字段名
        compressed = {}
        text_parts = []
        
        for table_name, table_info in list(tables.items())[:10]:  # 最多 10 个表
            compressed[table_name] = {
                "columns": [
                    {"name": col["name"]}
                    for col in table_info.get("columns", [])[:10]  # 每表最多 10 列
                ]
            }
            text_parts.append(f"{table_name}: {', '.join([c['name'] for c in compressed[table_name]['columns']])}")
        
        schema_text = "\n".join(text_parts)
        usage.prompt_tokens = self.count_tokens(schema_text)
        usage.total_tokens = usage.prompt_tokens
        
        return compressed, usage
    
    def _estimate_cost(self, usage: TokenUsage) -> float:
        """估算成本（美元）"""
        # 近似价格（每 1000 token）
        prices = {
            "gpt-4o": 0.005,
            "gpt-4-turbo": 0.01,
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0005,
            "claude-3-haiku": 0.00025,
            "claude-3-sonnet": 0.003,
            "claude-3-opus": 0.015,
        }
        
        price = prices.get(self.model, 0.005)
        return (usage.total_tokens / 1000) * price


class ResultSummarizer:
    """
    结果摘要器
    对查询结果进行摘要，避免直接发送大量数据给大模型
    """
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def summarize_for_analysis(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        max_rows: int = 100
    ) -> str:
        """
        为分析目的摘要数据
        
        Args:
            data: 查询结果
            columns: 列名
            max_rows: 最大行数
            
        Returns:
            摘要文本
        """
        if not data:
            return "查询结果为空"
        
        summary_parts = []
        
        # 1. 基本统计
        summary_parts.append(f"数据概览：")
        summary_parts.append(f"  - 总行数：{len(data)}")
        summary_parts.append(f"  - 列数：{len(columns)}")
        summary_parts.append(f"  - 列名：{', '.join(columns)}")
        
        # 2. 采样数据（前 N 行）
        sample_size = min(max_rows, len(data))
        summary_parts.append(f"\n数据采样（前{sample_size}行）：")
        
        for i, row in enumerate(data[:sample_size]):
            row_str = ", ".join([f"{k}={v}" for k, v in list(row.items())[:5]])
            summary_parts.append(f"  {i+1}. {row_str}")
        
        if len(data) > sample_size:
            summary_parts.append(f"  ... 还有 {len(data) - sample_size} 行")
        
        # 3. 数值列统计
        numeric_stats = self._calculate_numeric_stats(data, columns)
        if numeric_stats:
            summary_parts.append("\n数值列统计：")
            for col, stats in numeric_stats.items():
                summary_parts.append(
                    f"  {col}: 平均={stats['avg']:.2f}, "
                    f"最小={stats['min']}, 最大={stats['max']}"
                )
        
        summary_text = "\n".join(summary_parts)
        
        # 检查 token 数
        tokens = len(self.tokenizer.encode(summary_text))
        if tokens > self.max_tokens:
            # 进一步压缩
            summary_text = self._compress_summary(summary_text, self.max_tokens)
        
        return summary_text
    
    def _calculate_numeric_stats(
        self,
        data: List[Dict],
        columns: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """计算数值列统计"""
        stats = {}
        
        for col in columns[:10]:  # 最多分析 10 列
            values = []
            for row in data[:1000]:  # 最多采样 1000 行
                val = row.get(col)
                if isinstance(val, (int, float)):
                    values.append(val)
            
            if values:
                stats[col] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        
        return stats
    
    def _compress_summary(self, summary: str, max_tokens: int) -> str:
        """压缩摘要"""
        tokens = self.tokenizer.encode(summary)
        if len(tokens) <= max_tokens:
            return summary
        
        # 截断
        compressed_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(compressed_tokens) + "...[已压缩]"


class TokenBudget:
    """
    Token 预算管理
    跟踪和控制 token 使用
    """
    
    def __init__(
        self,
        max_tokens: int = 100000,
        max_cost_usd: float = 1.0
    ):
        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.used_tokens = 0
        self.estimated_cost = 0.0
        self.request_count = 0
    
    def can_use_tokens(self, estimated_tokens: int) -> Tuple[bool, Optional[str]]:
        """检查是否可以使用 token"""
        if self.used_tokens + estimated_tokens > self.max_tokens:
            return False, f"超出 token 预算 ({self.used_tokens + estimated_tokens} > {self.max_tokens})"
        
        return True, None
    
    def record_usage(self, tokens: int, cost: float):
        """记录 token 使用"""
        self.used_tokens += tokens
        self.estimated_cost += cost
        self.request_count += 1
    
    def get_usage_report(self) -> Dict[str, Any]:
        """获取使用报告"""
        return {
            "used_tokens": self.used_tokens,
            "max_tokens": self.max_tokens,
            "remaining_tokens": self.max_tokens - self.used_tokens,
            "usage_percent": (self.used_tokens / self.max_tokens) * 100,
            "estimated_cost_usd": self.estimated_cost,
            "max_cost_usd": self.max_cost_usd,
            "request_count": self.request_count
        }
    
    def reset(self):
        """重置预算"""
        self.used_tokens = 0
        self.estimated_cost = 0.0
        self.request_count = 0


# 全局实例
schema_optimizer = SchemaOptimizer()
result_summarizer = ResultSummarizer()
token_budget = TokenBudget()

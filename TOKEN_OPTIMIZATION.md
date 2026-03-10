# Token 优化指南

## ⚠️ 问题分析

### 查询数据会消耗大模型 Token 吗？

**答案：分情况**

| 场景 | 是否经过大模型 | Token 消耗 | 风险等级 |
|-----|--------------|----------|---------|
| **SQL 生成** | ✅ 是 | Schema 信息 + Prompt | ⚠️ 中等 |
| **查询执行** | ❌ 否 | 无 | ✅ 安全 |
| **结果返回** | ❌ 否 | 直接返回用户 | ✅ 安全 |
| **AI 分析数据** | ✅ 是 | 数据 + Prompt | 🔴 高风险 |

---

## 🎯 当前系统的 Token 使用

### 1. SQL 生成阶段（经过大模型）

```
用户查询 → AI 代理 → 生成 SQL
         ↑
    Schema 上下文
```

**Token 消耗来源**：
- System Prompt（约 200-500 token）
- Schema 信息（主要消耗）
- 用户查询（约 50-100 token）

**Schema 消耗示例**：
```
假设有 50 个表，每个表 20 个字段
每个字段信息约 50 token
总 token = 50 × 20 × 50 = 50,000 token!

这可能超出：
- GPT-4: 8K 限制 ❌
- GPT-3.5: 16K 限制 ❌
- GPT-4-Turbo: 128K 限制 ⚠️ 接近
```

### 2. 查询执行阶段（不经过大模型）

```
SQL → 数据库 → 结果
      ↑
   直接执行，不经过 AI
```

**✅ 安全**：查询结果直接返回用户，不消耗大模型 Token

### 3. 数据分析阶段（如果添加，会经过大模型）

```
查询结果 → AI 分析 → 洞察
    ↑
  大量数据
```

**🔴 高风险**：
```
10,000 行数据 × 每行 100 token = 1,000,000 token!

成本估算（GPT-4o）：
1,000,000 token × $0.005/1000 = $5.00 单次查询！
```

---

## ✅ 优化方案

### 方案 1: Schema 优化（已实现）

**位置**: `utils/token_optimizer.py` - `SchemaOptimizer`

**优化策略**：
1. **智能选择相关表** - 基于查询关键词匹配
2. **限制表数量** - 最多 20 个表
3. **限制字段数** - 每表最多 15 个字段
4. **优先保留重要字段** - 主键、外键、常用字段
5. **压缩描述信息** - 限制长度

**使用前**：
```python
schema = {
    "tables": {
        "users": {
            "description": "用户信息表，存储所有注册用户的基本信息...",
            "columns": [
                {"name": "id", "type": "INT", "description": "主键..."},
                {"name": "username", "type": "VARCHAR(50)", "description": "..."},
                # ... 20 个字段
            ]
        },
        # ... 50 个表
    }
}
# Token: ~50,000
```

**优化后**：
```python
optimized_schema = {
    "tables": {
        "users": {  # 基于查询选择的相关表
            "description": "用户信息表",  # 压缩描述
            "columns": [
                {"name": "id", "type": "INT"},  # 只保留必要信息
                {"name": "username", "type": "VARCHAR"},
                # ... 最多 15 个字段
            ]
        },
        # ... 最多 20 个表
    }
}
# Token: ~5,000 (减少 90%)
```

**代码示例**：
```python
from utils.token_optimizer import schema_optimizer

# 优化 schema
optimized_schema, token_usage = schema_optimizer.optimize_schema(
    schema_info,
    query="查询用户订单",  # 用于智能选择相关表
    max_tables=20,
    max_columns_per_table=15
)

print(f"Token 使用：{token_usage.prompt_tokens}")
print(f"估算成本：${token_usage.estimated_cost_usd}")
```

---

### 方案 2: 结果摘要（已实现）

**位置**: `utils/token_optimizer.py` - `ResultSummarizer`

**如果需要对数据进行 AI 分析**，先摘要再发送：

```python
from utils.token_optimizer import result_summarizer

# 查询结果（10,000 行）
data = [...]  # 大量数据
columns = ["id", "name", "amount", ...]

# 摘要（而不是发送全部数据）
summary = result_summarizer.summarize_for_analysis(
    data=data,
    columns=columns,
    max_rows=100  # 只采样 100 行
)

# 发送摘要给 AI
ai_response = agent.invoke({
    "messages": [{
        "role": "user",
        "content": f"分析以下数据：\n{summary}"
    }]
})
```

**摘要内容**：
```
数据概览：
  - 总行数：10000
  - 列数：15
  - 列名：id, name, amount, status, created_at...

数据采样（前 100 行）：
  1. id=1, name=张三，amount=100, status=active...
  2. id=2, name=李四，amount=200, status=active...
  ...
  100. id=100, name=王五，amount=500, status=inactive...
  ... 还有 9900 行

数值列统计：
  amount: 平均=350.25, 最小=10, 最大=9999
  ...
```

**Token 对比**：
| 方式 | Token 数 | 成本（GPT-4o） |
|-----|---------|--------------|
| 发送全部数据 | ~1,000,000 | $5.00 |
| 发送摘要 | ~2,000 | $0.01 |
| **节省** | **99.8%** | **99.8%** |

---

### 方案 3: Token 预算管理（已实现）

**位置**: `utils/token_optimizer.py` - `TokenBudget`

```python
from utils.token_optimizer import token_budget

# 设置预算
token_budget = TokenBudget(
    max_tokens=100000,  # 最多 10 万 token
    max_cost_usd=1.0    # 最多 1 美元
)

# 使用前检查
can_use, reason = token_budget.can_use_tokens(estimated_tokens=5000)
if not can_use:
    raise Exception(f"Token 预算不足：{reason}")

# 记录使用
token_budget.record_usage(tokens=4500, cost=0.0225)

# 查看报告
report = token_budget.get_usage_report()
print(f"已使用：{report['used_tokens']} / {report['max_tokens']}")
print(f"剩余：{report['remaining_tokens']}")
print(f"成本：${report['estimated_cost_usd']} / ${report['max_cost_usd']}")
```

---

## 📊 优化效果对比

### Schema 优化

| 场景 | 优化前 Token | 优化后 Token | 节省 |
|-----|------------|------------|------|
| 50 表×20 字段 | ~50,000 | ~5,000 | 90% |
| 100 表×30 字段 | ~150,000 | ~8,000 | 95% |
| 10 表×10 字段 | ~5,000 | ~3,000 | 40% |

### 数据摘要

| 数据量 | 原始 Token | 摘要 Token | 节省 |
|-------|----------|----------|------|
| 1,000 行 | ~100,000 | ~1,000 | 99% |
| 10,000 行 | ~1,000,000 | ~2,000 | 99.8% |
| 100,000 行 | ~10,000,000 | ~3,000 | 99.97% |

---

## 🛠️ 最佳实践

### 1. 始终优化 Schema

```python
# ✅ 推荐
agent.set_schema_context(schema_info, optimize=True)

# ❌ 不推荐（除非表很少）
agent.set_schema_context(schema_info, optimize=False)
```

### 2. 避免发送完整数据给 AI

```python
# ❌ 不推荐：发送全部数据
ai_response = agent.analyze(data=all_10000_rows)

# ✅ 推荐：发送摘要
summary = result_summarizer.summarize_for_analysis(data, columns)
ai_response = agent.analyze(data=summary)
```

### 3. 使用分页获取大数据

```python
# 查询大量数据
page = 1
all_insights = []

while True:
    response = client.post("/api/v1/query", json={
        "natural_query": "查询订单",
        "page": page,
        "page_size": 100
    })
    
    # 只分析当前页
    summary = summarize(response.json()["data"])
    insights = agent.analyze(summary)
    all_insights.extend(insights)
    
    if not response.json()["pagination_info"]["has_next"]:
        break
    page += 1
```

### 4. 设置 Token 预算

```python
# 生产环境建议
token_budget = TokenBudget(
    max_tokens=50000,     # 每次会话 5 万 token
    max_cost_usd=0.50     # 每次会话 0.5 美元
)
```

### 5. 监控 Token 使用

```python
# 在 API 响应中添加 token 信息
{
    "success": true,
    "data": [...],
    "token_usage": {
        "schema_tokens": 4500,
        "prompt_tokens": 5200,
        "completion_tokens": 800,
        "total_tokens": 6000,
        "estimated_cost_usd": 0.03
    }
}
```

---

## 💰 成本估算

### Token 价格（每 1000 token）

| 模型 | 输入价格 | 输出价格 |
|-----|---------|---------|
| GPT-3.5-Turbo | $0.0005 | $0.0015 |
| GPT-4o | $0.005 | $0.015 |
| GPT-4-Turbo | $0.01 | $0.03 |
| Claude-3-Haiku | $0.00025 | $0.00125 |
| Claude-3-Sonnet | $0.003 | $0.015 |
| Claude-3-Opus | $0.015 | $0.075 |

### 月度成本估算

**场景**：每日 1000 次查询

| 优化情况 | Token/查询 | 月 Token | 月成本（GPT-4o） |
|---------|----------|---------|----------------|
| ❌ 无优化 | 50,000 | 1.5B | $7,500 |
| ⚠️ 部分优化 | 5,000 | 150M | $750 |
| ✅ 完全优化 | 2,000 | 60M | $300 |

---

## 📈 监控指标

### Prometheus 指标

```prometheus
# Token 使用
llm_tokens_total{type="prompt"} 150000
llm_tokens_total{type="completion"} 30000

# 成本
llm_cost_total_usd 75.50

# Schema 优化
schema_optimization_ratio 0.10  # 优化后/优化前

# 预算使用
token_budget_used_percent 65.5
```

---

## 🔗 相关文件

| 文件 | 说明 |
|-----|------|
| `utils/token_optimizer.py` | Token 优化核心实现 |
| `core/agent.py` | AI 代理（已集成优化） |
| `DATA_LIMITS.md` | 数据量控制文档 |

---

## ✅ 总结

### 当前系统保护

| 保护项 | 状态 | 效果 |
|-------|------|------|
| Schema 优化 | ✅ 已实现 | 减少 90% Token |
| 结果不经过 AI | ✅ 默认 | 0 Token 消耗 |
| 结果摘要 | ✅ 已实现 | 减少 99% Token |
| Token 预算 | ✅ 已实现 | 防止超支 |
| 成本估算 | ✅ 已实现 | 实时追踪 |

### 关键建议

1. **查询结果默认不经过 AI** - 直接返回用户 ✅
2. **Schema 始终优化** - 减少 90% Token ✅
3. **如需 AI 分析，先摘要** - 减少 99% Token ✅
4. **设置预算限制** - 防止意外超支 ✅
5. **监控 Token 使用** - 及时发现异常 ✅

---

**文档版本**: 1.0  
**最后更新**: 2024

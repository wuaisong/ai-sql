# 数据量控制机制

## 📋 概述

企业级问数系统实现了**5 层防护机制**来防止查询数据过多导致的性能问题和资源滥用。

```
┌─────────────────────────────────────────────────────────┐
│                   用户查询请求                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 1: 配额检查 (QuotaChecker)                        │
│  - 并发查询数限制                                        │
│  - 每小时查询次数限制                                    │
│  - 每日查询行数限制                                      │
│  - 用户级别配额                                          │
└────────────────────┬────────────────────────────────────┘
                     │ ✓ 通过
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: SQL 验证 (SQLValidator)                         │
│  - 危险操作拦截                                          │
│  - WHERE 条件检查（大表）                                 │
│  - LIMIT 自动添加                                         │
│  - JOIN 数量限制                                          │
└────────────────────┬────────────────────────────────────┘
                     │ ✓ 通过
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: 大表保护 (LargeTableProtector)                 │
│  - 表大小统计                                            │
│  - 大表强制 WHERE                                        │
│  - 索引使用检查                                          │
│  - 成本估算 (EXPLAIN)                                    │
└────────────────────┬────────────────────────────────────┘
                     │ ✓ 通过
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4: 执行保护 (Connector)                           │
│  - 查询超时控制                                          │
│  - 连接池管理                                            │
│  - 流式结果处理                                          │
└────────────────────┬────────────────────────────────────┘
                     │ ✓ 完成
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 5: 结果处理 (ResultLimiter)                       │
│  - 行数截断                                              │
│  - 分页返回                                              │
│  - 元信息标注                                            │
│  - 使用情况记录                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
              返回给用户
```

---

## 🔧 各层详细说明

### Layer 1: 配额检查 (QuotaChecker)

**位置**: `services/quota.py`

**功能**:
- ✅ 并发查询数控制
- ✅ 频率限制（每小时/每日）
- ✅ 行数配额管理
- ✅ 用户级别差异化配置

**配置示例**:
```python
from services.quota import QuotaConfig, quota_checker

config = QuotaConfig(
    # 行数限制
    max_rows_per_query=10000,      # 单次查询最大 1 万行
    max_rows_per_day=1000000,      # 每日最大 100 万行
    soft_limit_rows=1000,          # 超过 1000 行警告
    
    # 频率限制
    max_queries_per_hour=100,      # 每小时 100 次
    max_queries_per_day=10000,     # 每日 1 万次
    
    # 时间限制
    max_execution_time_seconds=60, # 最大 60 秒
    soft_timeout_seconds=30,       # 超过 30 秒警告
    
    # 并发限制
    max_concurrent_queries=5,      # 最多 5 个并发
    
    # 大表保护
    large_table_threshold=1000000, # 100 万行以上为大表
    require_where_for_large_tables=True  # 大表强制 WHERE
)

quota_checker = QuotaChecker(config)
```

**用户级别配置**:
```python
# VIP 用户更高配额
config.user_quotas = {
    "vip_user_123": {
        "max_rows_per_query": 50000,
        "max_rows_per_day": 5000000,
        "max_queries_per_hour": 500
    },
    "restricted_user_456": {
        "max_rows_per_query": 1000,
        "max_rows_per_day": 10000,
        "max_queries_per_hour": 10
    }
}
```

**API 使用**:
```python
# 检查配额
allowed, reject_reason, warnings = quota_checker.check_query_quota(
    user_id="user_123",
    estimated_rows=5000
)

if not allowed:
    raise HTTPException(429, reject_reason)

# 记录使用
quota_checker.record_query(
    user_id="user_123",
    actual_rows=3500,
    execution_time_seconds=2.5
)
```

---

### Layer 2: SQL 验证 (SQLValidator)

**位置**: `core/sql_generator.py`

**功能**:
- ✅ 自动添加 LIMIT
- ✅ WHERE 条件检查
- ✅ 危险操作拦截
- ✅ 复杂度警告

**关键代码**:
```python
def _build_limit_clause(self, limit: Optional[int]) -> str:
    """构建 LIMIT 子句"""
    if not limit:
        return " LIMIT 100"  # 默认限制
    return f" LIMIT {min(limit, 10000)}"  # 最大 1 万

def validate(self, sql: str) -> SQLValidationResult:
    warnings = []
    
    # 检查缺少 WHERE
    if "WHERE" not in sql.upper() and "SELECT" in sql.upper():
        warnings.append("查询缺少 WHERE 条件，可能返回大量数据")
    
    # 检查缺少 LIMIT
    if "LIMIT" not in sql.upper() and "SELECT" in sql.upper():
        warnings.append("查询缺少 LIMIT，建议添加行数限制")
    
    # 检查 CROSS JOIN
    if "CROSS JOIN" in sql.upper():
        warnings.append("CROSS JOIN 可能导致大量数据")
    
    # 检查 JOIN 数量
    join_count = sql.upper().count("JOIN")
    if join_count > 5:
        warnings.append(f"查询包含 {join_count} 个 JOIN，可能影响性能")
```

---

### Layer 3: 大表保护 (LargeTableProtector)

**位置**: `services/quota.py`

**功能**:
- ✅ 表大小统计
- ✅ 大表识别
- ✅ 强制 WHERE 条件
- ✅ 查询成本估算

**使用示例**:
```python
from services.quota import large_table_protector

# 更新表统计
large_table_protector.update_table_stats(
    table_name="orders",
    row_count=5000000,  # 500 万行
    last_updated=datetime.utcnow()
)

# 验证查询
allowed, reject_reason, warnings = large_table_protector.validate_large_table_query(
    sql="SELECT * FROM orders WHERE status='active'",
    tables=["orders"]
)

if not allowed:
    # reject_reason = "大表 'orders' 查询必须包含 WHERE 条件"
    raise HTTPException(400, reject_reason)
```

**成本估算器**:
```python
from services.quota import QueryCostEstimator

estimator = QueryCostEstimator(connector=mysql_connector)

cost_info = estimator.estimate_cost("SELECT * FROM users WHERE id=1")
# 返回：
# {
#     'estimated_rows': 1,
#     'estimated_cost': 'low',
#     'scan_type': 'indexed_lookup',
#     'uses_index': True,
#     'warnings': []
# }
```

---

### Layer 4: 执行保护 (Connector)

**位置**: `connectors/base.py`, `connectors/mysql.py`

**功能**:
- ✅ 查询超时控制
- ✅ 连接池管理
- ✅ 自动 LIMIT 注入

**关键配置**:
```python
# SQLAlchemy 引擎配置
self.engine = create_engine(
    connection_url,
    pool_size=5,           # 基础连接数
    max_overflow=10,       # 最大溢出
    pool_recycle=3600,     # 1 小时回收
    pool_pre_ping=True,    # 健康检查
    connect_args={
        'connect_timeout': 10,  # 连接超时
        'read_timeout': 60      # 读取超时
    }
)

# 执行查询
def execute_query(self, sql: str, limit: int = 10000, timeout: int = 60):
    # 自动添加 LIMIT
    if "LIMIT" not in sql.upper():
        sql = f"{sql.rstrip(';')} LIMIT {limit}"
    
    # 设置超时
    with self.engine.connect() as conn:
        conn.execution_options(stream_results=True, execution_timeout=timeout)
        result = conn.execute(text(sql))
        return result.fetchall()
```

---

### Layer 5: 结果处理 (ResultLimiter)

**位置**: `services/quota.py`

**功能**:
- ✅ 行数截断
- ✅ 分页返回
- ✅ 元信息标注
- ✅ 截断警告

**使用示例**:
```python
from services.quota import result_limiter

# 限制行数
data, truncation_info = result_limiter.limit_rows(
    data=original_data,  # 假设有 50000 行
    max_rows=10000,
    truncate=True
)

# truncation_info:
# {
#     'original_rows': 50000,
#     'returned_rows': 10000,
#     'truncated': True,
#     'has_more': True,
#     'truncate_message': '结果已截断至 10000 行，原始数据 50000 行'
# }

# 分页返回
paginated_data, pagination_info = result_limiter.paginate(
    data=data,
    page=1,
    page_size=100,
    max_page_size=1000
)

# pagination_info:
# {
#     'page': 1,
#     'page_size': 100,
#     'total_rows': 10000,
#     'total_pages': 100,
#     'has_next': True,
#     'has_prev': False,
#     'next_page': 2,
#     'prev_page': None
# }
```

---

## 📊 API 响应示例

### 查询响应（包含数据量控制信息）

```json
{
  "success": true,
  "data": [...],
  "columns": ["id", "username", "email"],
  "row_count": 100,
  "sql": "SELECT * FROM users WHERE status='active'",
  "execution_time_ms": 125.5,
  "confidence": 0.85,
  
  // 数据量控制信息
  "truncation_info": {
    "original_rows": 50000,
    "returned_rows": 10000,
    "truncated": true,
    "has_more": true,
    "truncate_message": "结果已截断至 10000 行"
  },
  
  "pagination_info": {
    "page": 1,
    "page_size": 100,
    "total_rows": 10000,
    "total_pages": 100,
    "has_next": true,
    "next_page": 2
  },
  
  "warnings": [
    "查询行数较大 (50000)，建议添加过滤条件",
    "表 'users' 是大表，请确保使用索引"
  ],
  
  "quota_info": {
    "rows_used": 50000,
    "rows_remaining": 950000
  }
}
```

### 配额使用情况

```bash
GET /api/v1/quota/usage
```

```json
{
  "user_id": "user_123",
  "period": {
    "hourly": {
      "limit": 100,
      "used": 15,
      "remaining": 85,
      "resets_in": "0:45:30"
    },
    "daily": {
      "rows_limit": 1000000,
      "rows_used": 350000,
      "rows_remaining": 650000,
      "queries_limit": 10000,
      "queries_used": 150,
      "resets_in": "18:30:00"
    }
  },
  "concurrent": {
    "limit": 5,
    "current": 2,
    "available": 3
  }
}
```

---

## 🚨 错误响应

### 429 Too Many Requests - 配额超限

```json
{
  "detail": "每小时查询次数已达上限 (100)",
  "error_code": "QUOTA_EXCEEDED",
  "quota_type": "queries_per_hour",
  "limit": 100,
  "used": 100,
  "resets_in": "0:30:00"
}
```

### 400 Bad Request - 大表保护

```json
{
  "detail": "大表 'orders' 查询必须包含 WHERE 条件",
  "error_code": "LARGE_TABLE_PROTECTION",
  "table": "orders",
  "row_count": 5000000,
  "suggestion": "请添加 WHERE 条件过滤数据，例如：WHERE created_at > '2024-01-01'"
}
```

### 408 Request Timeout - 查询超时

```json
{
  "detail": "查询执行超时 (60 秒)",
  "error_code": "QUERY_TIMEOUT",
  "timeout_seconds": 60,
  "suggestion": "请优化查询或添加更多过滤条件"
}
```

---

## 🎯 最佳实践

### 1. 合理设置配额

```python
# 开发环境
dev_config = QuotaConfig(
    max_rows_per_query=1000,
    max_rows_per_day=10000,
    max_queries_per_hour=50
)

# 生产环境
prod_config = QuotaConfig(
    max_rows_per_query=10000,
    max_rows_per_day=1000000,
    max_queries_per_hour=100
)

# VIP 用户
vip_config = QuotaConfig(
    max_rows_per_query=50000,
    max_rows_per_day=5000000,
    max_queries_per_hour=500
)
```

### 2. 使用分页

```python
# 推荐：使用分页获取大量数据
response = client.post("/api/v1/query", json={
    "natural_query": "查询所有订单",
    "limit": 10000,
    "page": 1,
    "page_size": 100
})

# 遍历所有页
while response.json()["pagination_info"]["has_next"]:
    next_page = response.json()["pagination_info"]["next_page"]
    response = client.post("/api/v1/query", json={
        "natural_query": "查询所有订单",
        "page": next_page
    })
```

### 3. 添加过滤条件

```sql
-- ❌ 不推荐：全表扫描
SELECT * FROM orders

-- ✅ 推荐：添加 WHERE 和 LIMIT
SELECT * FROM orders 
WHERE created_at >= '2024-01-01' 
  AND status = 'active'
LIMIT 1000
```

### 4. 监控配额使用

```python
# 定期检查配额使用
usage = client.get("/api/v1/quota/usage").json()

if usage["period"]["daily"]["rows_remaining"] < 100000:
    print("警告：每日行数配额即将用完")
    
if usage["concurrent"]["available"] == 0:
    print("警告：并发查询数已达上限")
```

---

## 📈 监控指标

### Prometheus 指标

```prometheus
# 查询行数
query_rows_total{user_id="user_123"} 350000

# 查询次数
query_count_total{user_id="user_123"} 150

# 配额超限次数
quota_exceeded_total{type="rows_per_day"} 5

# 大表查询次数
large_table_queries_total{table="orders"} 25

# 结果截断次数
result_truncated_total 120

# 平均查询时间
query_duration_seconds_avg 0.125
```

---

## 🔗 相关文件

| 文件 | 说明 |
|-----|------|
| `services/quota.py` | 配额和限制核心实现 |
| `api/routes.py` | API 路由（集成数据量控制） |
| `core/sql_generator.py` | SQL 生成和验证 |
| `connectors/base.py` | 连接器基础类 |

---

**文档版本**: 1.0  
**最后更新**: 2024

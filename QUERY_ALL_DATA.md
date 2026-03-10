# 查询所有数据指南

## 🎯 场景说明

当你需要查询**全部数据**（而不是限制行数）时，系统提供多种方案：

| 数据量 | 推荐方案 | 说明 |
|-------|---------|------|
| < 1 万行 | 直接查询 | 默认 LIMIT 10000 |
| 1 万 - 100 万行 | 分页查询 / 导出任务 | 分批获取或导出文件 |
| 100 万 - 1000 万行 | 后台导出任务 | 异步执行，完成后下载 |
| > 1000 万行 | 后台任务 + 分片 | 分片导出，避免单文件过大 |

---

## 📋 方案详解

### 方案 1: 直接查询（小数据量）

**适用**: < 10,000 行

```python
# API 调用
response = client.post("/api/v1/query", json={
    "natural_query": "查询所有活跃用户",
    "limit": 10000  # 最大允许值
})

data = response.json()["data"]
print(f"获取 {len(data)} 行数据")
```

**特点**：
- ✅ 简单直接
- ✅ 实时返回
- ⚠️ 受配额限制

---

### 方案 2: 分页查询（中等数据量）

**适用**: 10,000 - 1,000,000 行

```python
# 分页获取所有数据
all_data = []
page = 1

while True:
    response = client.post("/api/v1/query", json={
        "natural_query": "查询所有订单",
        "page": page,
        "page_size": 1000
    })
    
    result = response.json()
    all_data.extend(result["data"])
    
    print(f"已获取 {len(all_data)} 行")
    
    if not result["pagination_info"]["has_next"]:
        break
    page += 1

print(f"总共 {len(all_data)} 行")
```

**特点**：
- ✅ 内存友好
- ✅ 可控进度
- ⚠️ 需要多次请求

---

### 方案 3: 导出任务（推荐）

**适用**: 100,000 - 10,000,000 行

```python
# 1. 创建导出任务
response = client.post("/api/v1/export", json={
    "natural_query": "查询所有销售记录",
    "datasource_id": "mysql_main",
    "format": "csv"  # 或 json, jsonl
})

task_id = response.json()["task_id"]
print(f"任务 ID: {task_id}")

# 2. 查询进度
while True:
    status = client.get(f"/api/v1/export/{task_id}")
    task = status.json()
    
    print(f"进度：{task['progress_percent']:.1f}%")
    
    if task["status"] in ["completed", "failed"]:
        break
    
    time.sleep(2)

# 3. 下载文件
if task["status"] == "completed":
    file = client.get(f"/api/v1/export/{task_id}/download")
    
    with open("export.csv", "wb") as f:
        f.write(file.content)
    
    print(f"下载完成：{task['file_size']} 字节")
```

**特点**：
- ✅ 异步执行，不阻塞
- ✅ 支持超大数据
- ✅ 可下载离线使用
- ✅ 自动清理过期文件

---

### 方案 4: 估算后决策

**不确定数据量？先估算！**

```python
# 估算数据量
response = client.post("/api/v1/query/estimate", json={
    "natural_query": "查询所有用户订单",
    "datasource_id": "mysql_main"
})

estimate = response.json()
print(f"预估行数：{estimate['estimated_rows']}")
print(f"建议：{estimate['recommendation']}")

# 根据建议选择方案
if estimate['estimated_rows'] < 10000:
    # 直接查询
    ...
elif estimate['estimated_rows'] < 1000000:
    # 导出任务
    ...
else:
    # 后台任务
    ...
```

---

## 🚀 API 端点

### 创建导出任务

```http
POST /api/v1/export
Content-Type: application/json
Authorization: Bearer <token>

{
    "natural_query": "查询所有销售数据",
    "datasource_id": "mysql_main",
    "format": "csv",
    "options": {
        "batch_size": 10000,
        "compression": false
    }
}
```

**响应**：
```json
{
    "success": true,
    "task_id": "export_user_20240101120000",
    "status": "pending",
    "message": "导出任务已创建"
}
```

---

### 查询任务状态

```http
GET /api/v1/export/{task_id}
Authorization: Bearer <token>
```

**响应**：
```json
{
    "task_id": "export_user_20240101120000",
    "user_id": "user_123",
    "query": "查询所有销售数据",
    "format": "csv",
    "status": "running",
    "total_rows": 0,
    "exported_rows": 50000,
    "progress_percent": 25.5,
    "created_at": "2024-01-01T12:00:00",
    "estimated_completion": "2024-01-01T12:05:00"
}
```

---

### 下载导出文件

```http
GET /api/v1/export/{task_id}/download
Authorization: Bearer <token>
```

**响应**：文件流（CSV/JSON 等）

---

### 取消任务

```http
POST /api/v1/export/{task_id}/cancel
Authorization: Bearer <token>
```

---

### 列出我的任务

```http
GET /api/v1/export/tasks
Authorization: Bearer <token>
```

**响应**：
```json
{
    "tasks": [
        {
            "task_id": "export_001",
            "status": "completed",
            "format": "csv",
            "rows": 100000,
            "created_at": "2024-01-01T12:00:00"
        }
    ],
    "total": 1
}
```

---

### 估算数据量

```http
POST /api/v1/query/estimate
Content-Type: application/json
Authorization: Bearer <token>

{
    "natural_query": "查询所有订单",
    "datasource_id": "mysql_main"
}
```

**响应**：
```json
{
    "success": true,
    "estimated_rows": 500000,
    "recommendation": "数据量中等，建议导出为文件",
    "strategies": {
        "direct": "❌ 不推荐（数据量过大）",
        "pagination": "✅ 推荐",
        "export": "✅ 推荐"
    }
}
```

---

## 📊 导出格式

### CSV（推荐）

```csv
id,username,email,created_at
1,张三,zhangsan@example.com,2024-01-01
2,李四,lisi@example.com,2024-01-02
```

**优点**：
- ✅ 文件小
- ✅ 兼容性好
- ✅ 可用 Excel 打开

---

### JSON

```json
[
  {"id": 1, "username": "张三", "email": "zhangsan@example.com"},
  {"id": 2, "username": "李四", "email": "lisi@example.com"}
]
```

**优点**：
- ✅ 保留数据类型
- ✅ 支持嵌套结构
- ⚠️ 文件较大

---

### JSONL (JSON Lines)

```jsonl
{"id": 1, "username": "张三"}
{"id": 2, "username": "李四"}
```

**优点**：
- ✅ 流式处理友好
- ✅ 易于增量读取
- ✅ 内存友好

---

## ⚙️ 配置选项

### 配额调整

```python
# 为特殊用户提高配额
from services.quota import quota_checker, QuotaConfig

quota_checker.config.user_quotas["vip_user"] = {
    "max_rows_per_query": 1000000,  # 单次 100 万行
    "max_rows_per_day": 10000000,   # 每日 1000 万行
    "max_queries_per_hour": 500
}
```

### 导出配置

```python
from services.export import DataExporter

exporter = DataExporter(
    export_dir="./exports",      # 导出目录
    max_file_size=1024*1024*100, # 最大 100MB
    cleanup_days=7               # 7 天后清理
)
```

---

## 🛡️ 安全限制

### 默认限制

| 限制项 | 默认值 | 说明 |
|-------|-------|------|
| 单次查询行数 | 10,000 | 直接查询上限 |
| 导出任务行数 | 10,000,000 | 导出上限 |
| 并发导出任务 | 3 | 每用户最多 3 个 |
| 文件保留时间 | 7 天 | 自动清理 |
| 单文件大小 | 500MB | 超过则分片 |

### 提高限制

```python
# 联系管理员提高限制
# 需要提供：
# 1. 使用场景说明
# 2. 预估数据量
# 3. 使用频率
```

---

## 💡 最佳实践

### 1. 先估算，后查询

```python
# ✅ 推荐
estimate = client.post("/api/v1/query/estimate", ...)
if estimate["estimated_rows"] > 100000:
    # 使用导出
    ...
else:
    # 直接查询
    ...
```

### 2. 使用合适的格式

```python
# 数据分析 → CSV
format="csv"

# 程序处理 → JSON
format="json"

# 超大数据 → JSONL
format="jsonl"
```

### 3. 定期清理

```python
# 下载后及时删除
client.post(f"/api/v1/export/{task_id}/delete")
```

### 4. 监控进度

```python
# 轮询进度
while task["status"] == "running":
    print(f"进度：{task['progress_percent']}%")
    time.sleep(2)
    task = client.get(f"/api/v1/export/{task_id}").json()
```

---

## 📈 性能参考

### 导出速度

| 数据量 | 格式 | 预计时间 | 文件大小 |
|-------|------|---------|---------|
| 10 万行 | CSV | 10 秒 | 50MB |
| 100 万行 | CSV | 2 分钟 | 500MB |
| 1000 万行 | CSV | 20 分钟 | 5GB |
| 10 万行 | JSON | 15 秒 | 80MB |
| 100 万行 | JSON | 3 分钟 | 800MB |

*测试环境：8 核 CPU, 16GB 内存，SSD*

---

## 🔗 相关文件

| 文件 | 说明 |
|-----|------|
| `services/export.py` | 导出服务核心实现 |
| `api/routes.py` | API 路由（待更新） |
| `DATA_LIMITS.md` | 数据量控制文档 |
| `TOKEN_OPTIMIZATION.md` | Token 优化文档 |

---

## ✅ 总结

### 查询所有数据的正确姿势

1. **< 1 万行** → 直接查询 ✅
2. **1 万 - 100 万行** → 分页查询 或 导出任务 ✅
3. **100 万 - 1000 万行** → 导出任务 ✅
4. **> 1000 万行** → 后台任务 + 分片导出 ✅

### 关键建议

- ✅ 先估算数据量
- ✅ 选择合适格式（CSV/JSON/JSONL）
- ✅ 大数据使用导出任务
- ✅ 及时下载和清理文件
- ✅ 监控任务进度

---

**文档版本**: 1.0  
**最后更新**: 2024

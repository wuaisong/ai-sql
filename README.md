# 企业级问数系统 (Enterprise Data Query System)

基于 DeepAgents 的企业级自然语言数据查询系统，支持将自然语言转换为 SQL 查询，提供安全、高效、智能的数据访问能力。

## 🏗️ 系统架构

```
enterprise-data-query/
├── core/                    # 核心引擎
│   ├── __init__.py
│   ├── agent.py            # DeepAgents AI 代理引擎
│   ├── query_processor.py  # 查询处理管道
│   └── sql_generator.py    # SQL 生成/验证/优化
├── connectors/              # 数据源连接器
│   ├── __init__.py
│   ├── base.py             # 连接器基类
│   ├── mysql.py            # MySQL 连接器
│   └── postgresql.py       # PostgreSQL 连接器
├── services/                # 业务服务
│   ├── __init__.py
│   ├── auth.py             # 认证授权
│   ├── cache.py            # 缓存服务
│   └── audit.py            # 审计日志
├── api/                     # API 接口
│   ├── __init__.py
│   ├── routes.py           # 路由定义
│   └── middleware.py       # 中间件
├── models/                  # 数据模型
│   ├── __init__.py
│   └── query.py            # 查询模型
├── config/                  # 配置管理
│   ├── __init__.py
│   └── settings.py         # 系统配置
├── utils/                   # 工具函数
│   ├── __init__.py
│   ├── logger.py           # 日志工具
│   └── validators.py       # 验证工具
├── main.py                  # 入口文件
└── requirements.txt         # 依赖
```

## 🚀 核心模块详解

### 1. Core - 核心引擎

#### Agent (agent.py)
AI 代理引擎，负责自然语言到 SQL 的转换。

**核心类：**
- `DataQueryAgent` - 主代理类
- `AgentConfig` - 代理配置
- `AgentPool` - 代理池（负载均衡）
- `AgentMetrics` - 性能指标

**支持的代理角色：**
- `SQL_EXPERT` - SQL 专家
- `DATA_ANALYST` - 数据分析师
- `QUERY_OPTIMIZER` - 查询优化师
- `SCHEMA_EXPLORER` - Schema 探索者
- `VALIDATOR` - 验证器

**使用示例：**
```python
from core.agent import DataQueryAgent, AgentConfig, AgentRole

# 创建代理配置
config = AgentConfig(
    model="gpt-4",
    role=AgentRole.SQL_EXPERT,
    temperature=0.1,
    enable_cache=True
)

# 创建代理
agent = DataQueryAgent(config)
agent.initialize()

# 设置 schema 上下文
agent.set_schema_context({
    "database": "test_db",
    "tables": {
        "users": {
            "description": "用户表",
            "columns": [
                {"name": "id", "type": "INT", "description": "用户 ID"},
                {"name": "username", "type": "VARCHAR", "description": "用户名"}
            ]
        }
    }
})

# 生成 SQL
result = agent.generate_sql("查询所有活跃用户")
print(result.sql)
print(result.confidence)
```

#### Query Processor (query_processor.py)
查询处理管道，编排完整的查询流程。

**核心类：**
- `QueryProcessor` - 主处理器
- `QueryPipeline` - 处理管道
- `QueryContext` - 查询上下文
- `IntentRecognizer` - 意图识别器

**处理阶段：**
1. `RECEIVED` - 接收查询
2. `INTENT_ANALYSIS` - 意图分析
3. `SCHEMA_MATCHING` - Schema 匹配
4. `SQL_GENERATION` - SQL 生成
5. `SQL_VALIDATION` - SQL 验证
6. `SQL_OPTIMIZATION` - SQL 优化
7. `EXECUTION` - 执行查询
8. `RESULT_PROCESSING` - 结果处理
9. `COMPLETED` - 完成

**支持的查询意图：**
- `SIMPLE_SELECT` - 简单查询
- `AGGREGATION` - 聚合统计
- `TIME_SERIES` - 时间序列
- `COMPARISON` - 对比分析
- `TREND` - 趋势分析
- `RANKING` - 排名
- `FILTER` - 筛选
- `JOIN` - 多表关联

**使用示例：**
```python
from core.query_processor import QueryProcessor
from core.sql_generator import SQLGenerator, SQLValidator, SQLOptimizer

# 创建组件
generator = SQLGenerator()
validator = SQLValidator()
optimizer = SQLOptimizer()

# 创建处理器
processor = QueryProcessor(
    sql_generator=generator,
    sql_validator=validator,
    sql_optimizer=optimizer,
    connector=mysql_connector,
    cache_service=cache_service
)

# 设置 schema
processor.set_schema_context(schema_info)

# 处理查询
result = await processor.process_query(
    natural_query="统计最近 30 天的销售趋势",
    user_id="user_123",
    datasource_id="mysql_main"
)

print(f"成功：{result.success}")
print(f"SQL: {result.sql}")
print(f"数据：{result.data}")
```

#### SQL Generator (sql_generator.py)
SQL 生成、验证和优化。

**核心类：**
- `SQLGenerator` - SQL 生成器
- `SQLValidator` - SQL 验证器
- `SQLOptimizer` - SQL 优化器

**SQL 模板库：**
- `simple_select` - 简单查询
- `aggregation` - 聚合查询
- `time_series` - 时间序列
- `ranking` - 排名查询
- `join` - 关联查询
- `comparison` - 对比查询
- `trend` - 趋势查询

**验证检查项：**
- 危险操作检测（DROP、DELETE 等）
- SQL 注入模式识别
- 只读性验证
- 表名验证
- 复杂度警告

**优化建议：**
- 索引建议
- 查询重写建议
- 性能提升估计

**使用示例：**
```python
from core.sql_generator import create_sql_processor

# 创建 SQL 处理组件
generator, validator, optimizer = create_sql_processor(
    schema_context=schema_info,
    ai_agent=agent
)

# 生成 SQL
gen_result = generator.generate_sql("查询用户订单")
print(gen_result.sql)

# 验证 SQL
val_result = validator.validate(gen_result.sql)
print(f"有效：{val_result.is_valid}")
print(f"风险等级：{val_result.risk_level}")

# 优化 SQL
opt_result = optimizer.optimize(val_result.sql)
print(f"优化后：{opt_result.optimized_sql}")
print(f"性能提升：{opt_result.estimated_performance_gain}")
```

### 2. Connectors - 数据源连接器

支持多种数据库类型：

```python
from connectors import MySQLConnector, PostgreSQLConnector

# MySQL
connector = MySQLConnector(
    host="localhost",
    port=3306,
    database="test",
    username="root",
    password="password"
)
connector.connect()

# 执行查询
data, columns = connector.execute_query("SELECT * FROM users LIMIT 100")

# 获取 schema
schema = connector.get_schema()

# PostgreSQL
pg_connector = PostgreSQLConnector(
    host="localhost",
    port=5432,
    database="test",
    username="postgres",
    password="password"
)
```

### 3. Services - 业务服务

#### 认证服务
```python
from services.auth import auth_service

# 登录
user = auth_service.authenticate_user("username", "password")
if user:
    token = auth_service.create_access_token({
        "sub": user["user_id"],
        "username": user["username"]
    })

# 验证 token
token_data = auth_service.verify_token(token)

# 检查权限
has_permission = auth_service.check_permission(user, "read")
```

#### 缓存服务
```python
from services.cache import cache_service

# 设置缓存
cache_service.set("key", {"data": "value"}, expire=300)

# 获取缓存
value = cache_service.get("key")

# 缓存查询结果
cache_service.cache_query_result(sql, datasource_id, result)
```

#### 审计服务
```python
from services.audit import audit_logger

# 记录查询
audit_logger.log_query(
    user_id="user_123",
    username="admin",
    datasource_id="mysql_main",
    natural_query="查询用户",
    sql="SELECT * FROM users",
    success=True,
    row_count=100,
    execution_time_ms=50.5
)
```

## 📡 API 接口

### 启动服务
```bash
cd enterprise-data-query
pip install -r requirements.txt
python main.py
```

### API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/auth/me` | 获取当前用户 |
| POST | `/api/v1/query` | 执行查询 |
| GET | `/api/v1/datasources` | 获取数据源列表 |
| GET | `/api/v1/datasources/{id}/schema` | 获取 Schema |
| GET | `/api/v1/health` | 健康检查 |

### 查询示例
```bash
# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 执行查询
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "natural_query": "统计最近 30 天的销售趋势",
    "datasource_id": "demo_mysql",
    "use_cache": true,
    "limit": 1000
  }'
```

## ⚙️ 配置

创建 `.env` 文件：
```env
# 应用配置
APP_NAME=Enterprise Data Query System
DEBUG=False

# API 配置
HOST=0.0.0.0
PORT=8000

# 安全配置
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# DeepAgents 配置
DEEPAGENTS_MODEL=gpt-4
DEEPAGENTS_API_KEY=your-api-key

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 查询限制
MAX_QUERY_ROWS=10000
QUERY_TIMEOUT_SECONDS=60
```

## 🔒 安全特性

1. **SQL 注入防护** - 多层检测和拦截
2. **只读查询** - 禁止数据修改操作
3. **权限控制** - 基于角色的访问控制
4. **审计日志** - 完整的操作记录
5. **查询限制** - 行数和超时限制
6. **参数化查询** - 防止 SQL 注入

## 📊 性能优化

1. **查询缓存** - Redis/内存缓存
2. **代理池** - 负载均衡
3. **SQL 优化** - 自动优化建议
4. **连接池** - 数据库连接复用
5. **异步处理** - 高性能 I/O

## 🧪 测试

```bash
pytest tests/ -v
```

## 📝 许可证

MIT License
#   a i - s q l  
 
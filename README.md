# 企业级问数系统 (Enterprise Data Query System)

基于 DeepAgents 的企业级自然语言数据查询系统，支持将自然语言转换为 SQL 查询，提供安全、高效、智能的数据访问能力。

## 🎯 特性亮点

### 🤖 智能查询
- **自然语言转 SQL** - 使用 AI 理解用户意图
- **多数据源支持** - MySQL、PostgreSQL、Oracle、SQLite
- **查询优化** - 自动优化和索引建议

### 🔒 企业级安全
- **权限控制** - 基于角色的访问控制
- **审计日志** - 完整的操作记录
- **SQL 防护** - 多层安全检测和拦截

### 🚀 高性能
- **连接池** - 数据库连接复用
- **智能缓存** - Redis/内存多级缓存
- **异步处理** - 高性能 I/O 操作

### 📊 可观测性
- **实时监控** - 系统指标和性能数据
- **健康检查** - 自动服务状态检测
- **详细日志** - 结构化日志记录

## 🚀 快速部署

### 使用 Docker Compose（推荐）
```bash
# 1. 克隆项目
git clone <repository-url>
cd enterprise-data-query

# 2. 一键部署
./deploy.sh init
./deploy.sh start

# 3. 访问应用
# http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 手动部署
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 文件

# 3. 启动服务
./start.sh dev
```

### 生产环境部署
```bash
# 使用生产配置
docker-compose -f docker-compose.yml --env-file .env.production up -d

# 详细部署指南请查看 DEPLOYMENT.md
```

## 📋 部署摘要

### 🎯 核心部署目标
- **快速启动**：5分钟内完成开发环境部署
- **生产就绪**：支持高可用、可扩展的生产部署
- **安全合规**：内置企业级安全特性和审计功能
- **易于维护**：完整的监控、备份和恢复机制

### 🏗️ 部署架构概览
```
企业级问数系统架构
├── 应用层 (FastAPI)          :8000
│   ├── API 网关
│   ├── 查询引擎
│   └── 安全管理
├── 数据层
│   ├── Redis 缓存           :6379
│   ├── MySQL 示例数据库     :3306 (可选)
│   └── PostgreSQL 示例数据库:5432 (可选)
└── 基础设施层
    ├── Docker 容器化
    ├── Nginx 反向代理       :80/443
    └── 监控和日志系统
```

### ⚡ 部署时间预估
| 环境类型 | 部署时间 | 复杂度 | 所需技能 |
|----------|----------|--------|----------|
| 开发环境 | 5-10分钟 | ⭐☆☆☆☆ | 基础 Docker 知识 |
| 测试环境 | 15-20分钟 | ⭐⭐☆☆☆ | 熟悉 Docker Compose |
| 生产环境 | 30-60分钟 | ⭐⭐⭐⭐☆ | 运维经验，了解 SSL、负载均衡 |

### 🔧 关键配置项
1. **环境变量**：必须配置 `SECRET_KEY`、`DEEPAGENTS_API_KEY`
2. **数据库连接**：支持 MySQL、PostgreSQL、Oracle、SQLite
3. **缓存配置**：Redis 连接和密码设置
4. **安全设置**：HTTPS 证书、CORS 配置、访问控制

### 📊 资源需求
| 组件 | 开发环境 | 测试环境 | 生产环境 |
|------|----------|----------|----------|
| CPU | 2核 | 4核 | 8核 |
| 内存 | 4GB | 8GB | 16GB |
| 存储 | 10GB | 30GB | 100GB+ |
| 网络 | 100Mbps | 500Mbps | 1Gbps |

### 🚀 一键部署命令
```bash
# 完整部署流程
git clone <repository-url>
cd enterprise-data-query
./deploy.sh init    # 初始化环境
./deploy.sh start   # 启动所有服务
./deploy.sh status  # 检查服务状态
```

### 🔄 升级和维护
```bash
# 版本升级
./deploy.sh backup    # 备份当前版本
git pull origin main  # 更新代码
./deploy.sh restart   # 重启服务

# 日常维护
./deploy.sh logs      # 查看日志
./deploy.sh backup    # 定期备份
./deploy.sh update    # 更新依赖
```

### 🛡️ 安全部署检查清单
- [ ] 生成强密码和密钥
- [ ] 配置 HTTPS 证书
- [ ] 设置防火墙规则
- [ ] 启用审计日志
- [ ] 配置定期备份
- [ ] 设置监控告警
- [ ] 实施访问控制
- [ ] 进行安全扫描

### 📈 性能优化建议
1. **数据库优化**：为常用查询字段添加索引
2. **缓存策略**：调整缓存过期时间
3. **连接池**：根据并发量调整连接池大小
4. **查询限制**：设置合理的行数和超时限制

### 🆘 故障排除
- **端口冲突**：修改 `.env` 中的端口配置
- **内存不足**：增加 Docker 内存限制
- **连接失败**：检查网络和数据库配置
- **权限问题**：检查文件权限和用户配置

### 📞 获取帮助
- 查看详细部署文档：[DEPLOYMENT.md](DEPLOYMENT.md)
- 访问在线 API 文档：`http://localhost:8000/docs`
- 检查系统日志：`logs/` 目录
- 提交 Issue 获取技术支持

**部署成功标志**：访问 `http://localhost:8000/api/v1/system/health` 返回健康状态，且所有服务正常运行。

## 📋 系统要求

| 环境 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 开发环境 | 2核 CPU, 4GB 内存 | 4核 CPU, 8GB 内存 |
| 生产环境 | 4核 CPU, 8GB 内存 | 8核 CPU, 16GB 内存 |
| 存储 | 10GB SSD | 50GB SSD |
| 网络 | 100Mbps | 1Gbps |

## 🔧 核心功能

### 1. 智能查询处理
- 自然语言理解
- SQL 生成和验证
- 查询优化建议
- 多表关联支持

### 2. 数据源管理
- 多数据库支持
- 连接池管理
- Schema 自动发现
- 连接测试和监控

### 3. 用户和权限
- 多角色支持（管理员、分析师、访客）
- 细粒度权限控制
- 配额管理
- 审计日志

### 4. 监控和运维
- 实时系统指标
- 健康检查
- 日志聚合
- 备份和恢复

## 📡 API 接口示例

### 用户认证
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \n  -H "Content-Type: application/json" \n  -d '{"username": "admin", "password": "admin123"}'
```

### 执行查询
```bash
curl -X POST http://localhost:8000/api/v1/query \n  -H "Authorization: Bearer <token>" \n  -H "Content-Type: application/json" \n  -d '{
    "natural_query": "统计最近30天的销售趋势",
    "datasource_id": "demo_mysql",
    "use_cache": true
  }'
```

### 系统监控
```bash
curl http://localhost:8000/api/v1/system/health
curl http://localhost:8000/api/v1/system/metrics
```

## 🐳 Docker 服务架构

```
企业级问数系统
├── app (主应用)        :8000     # FastAPI 应用
├── redis (缓存)        :6379     # Redis 缓存服务
├── mysql-demo (示例)   :3306     # MySQL 示例数据库
├── postgres-demo (示例):5432     # PostgreSQL 示例数据库
└── nginx (反向代理)    :80/443   # 生产环境反向代理
```

## 🔄 更新和维护

### 日常维护
```bash
# 查看服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs app

# 备份数据
./deploy.sh backup
```

### 版本升级
```bash
# 1. 备份当前版本
./deploy.sh backup

# 2. 更新代码
git pull origin main

# 3. 重启服务
./deploy.sh restart
```

## 🚨 故障排除

### 常见问题
1. **端口冲突** - 修改 .env 中的 PORT 设置
2. **内存不足** - 增加 Docker 内存限制
3. **连接失败** - 检查数据库配置和网络
4. **权限问题** - 检查文件权限和用户配置

### 获取帮助
- 查看 [API 文档](http://localhost:8000/docs)
- 检查系统日志 (`logs/` 目录)
- 查阅 [DEPLOYMENT.md](DEPLOYMENT.md)
- 提交 Issue 获取支持

## 📈 性能优化建议

### 数据库优化
```sql
-- 为常用查询字段添加索引
CREATE INDEX idx_users_created ON users(created_at);
CREATE INDEX idx_orders_date ON orders(order_date);
```

### 缓存策略
```python
# 调整缓存时间
CACHE_EXPIRE_SECONDS = 600      # 查询缓存10分钟
SCHEMA_CACHE_TTL = 3600         # Schema缓存1小时
```

### 连接池配置
```python
# 增加连接池大小
CONNECTION_POOL_MAX_SIZE = 50
CONNECTION_POOL_IDLE_TIMEOUT = 300
```

## 🔐 安全最佳实践

### 生产环境配置
1. **使用强密码** - 设置复杂的 SECRET_KEY 和数据库密码
2. **启用 HTTPS** - 配置 SSL 证书
3. **限制访问** - 配置防火墙和 CORS
4. **定期备份** - 实施自动化备份策略

### 监控和告警
1. **健康检查** - 设置定期健康检查
2. **日志监控** - 监控异常日志
3. **性能告警** - 设置性能阈值告警
4. **安全扫描** - 定期进行安全扫描

## 🤝 贡献指南

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**开始使用**
- 🐳 [Docker 部署指南](DEPLOYMENT.md#docker-部署)
- 🏗️ [生产环境部署](DEPLOYMENT.md#生产环境部署)
- 🔧 [配置说明](DEPLOYMENT.md#配置说明)
- 📊 [监控和维护](DEPLOYMENT.md#监控和维护)

**需要帮助？**
- 📖

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

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Redis 5.0+ (可选，用于缓存)
- MySQL/PostgreSQL (数据源，可选)

### 安装依赖
```bash
# 克隆项目
git clone <repository-url>
cd enterprise-data-query

# 安装 Python 依赖
pip install -r requirements.txt
```

### 配置环境
```bash
# 复制环境文件
cp .env.example .env

# 编辑配置文件
# 设置 SECRET_KEY、DEEPAGENTS_API_KEY 等
```

### 初始化数据库
```bash
# 创建数据库表
python migrations.py create

# 创建示例数据（可选）
python migrations.py seed
```

### 启动服务
```bash
# 开发模式（热重载）
./start.sh dev

# 或直接运行
python main.py
```

### 访问应用
- 应用地址: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/v1/system/health

## 📡 API 接口

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

## 🐳 Docker 部署

### 使用 Docker Compose（推荐）

```bash
# 1. 初始化部署环境
./deploy.sh init

# 2. 启动所有服务
./deploy.sh start

# 3. 查看服务状态
./deploy.sh status

# 4. 查看日志
./deploy.sh logs app
```

### 服务说明
- **app**: 主应用服务 (端口: 8000)
- **redis**: Redis 缓存服务 (端口: 6379)
- **mysql-demo**: MySQL 示例数据库 (端口: 3306，可选)
- **postgres-demo**: PostgreSQL 示例数据库 (端口: 5432，可选)
- **nginx**: 反向代理 (端口: 80/443，生产环境)

### 环境变量配置
创建 `.env` 文件：
```env
# 应用配置
DEBUG=false
SECRET_KEY=必须设置32位以上随机字符串

# DeepAgents 配置
DEEPAGENTS_API_KEY=您的API密钥

# Redis 配置
REDIS_PASSWORD=强密码

# 数据库配置
MYSQL_ROOT_PASSWORD=root
POSTGRES_PASSWORD=postgres
```

### 生成安全密钥
```bash
# 生成 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成 Redis 密码
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

## 🏗️ 生产环境部署

### 1. 准备工作
```bash
# 克隆代码
git clone <repository-url>
cd enterprise-data-query

# 切换到生产分支
git checkout main

# 创建生产环境配置
cp .env.production .env
# 编辑 .env 文件，设置所有必要的配置
```

### 2. 使用 Docker Compose 部署
```bash
# 使用生产配置启动
docker-compose -f docker-compose.yml --env-file .env up -d

# 查看服务状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app
```

### 3. 数据库迁移
```bash
# 进入容器执行迁移
docker-compose exec app python migrations.py create

# 创建管理员用户（可选）
docker-compose exec app python -c "
from services.auth import pwd_context
from models.database import get_db, User
import uuid

db = get_db()
user = User(
    id=str(uuid.uuid4()),
    username='admin',
    email='admin@example.com',
    hashed_password=pwd_context.hash('Admin@123'),
    role='admin'
)
db.add(user)
db.commit()
print('管理员用户创建成功')
"
```

### 4. 配置反向代理（Nginx）
```bash
# 生成 SSL 证书（生产环境）
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=Company/CN=yourdomain.com"

# 启动 Nginx
docker-compose up -d nginx
```

### 5. 监控和维护
```bash
# 健康检查
curl https://yourdomain.com/api/v1/system/health

# 系统指标
curl https://yourdomain.com/api/v1/system/metrics

# 备份数据
./deploy.sh backup

# 重启服务
./deploy.sh restart
```

## 🔧 高级配置

### 自定义数据源连接
```yaml
# 在 docker-compose.yml 中添加自定义数据源
services:
  custom-mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: custom_password
      MYSQL_DATABASE: business_data
    volumes:
      - mysql_business_data:/var/lib/mysql
    ports:
      - "3307:3306"
```

### 配置持久化存储
```yaml
# 在 docker-compose.yml 中配置卷
volumes:
  app_data:
    driver: local
    driver_opts:
      type: none
      device: /path/to/persistent/storage
      o: bind
```

### 设置资源限制
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## 📊 监控和日志

### 内置监控端点
- `/api/v1/system/health` - 健康检查
- `/api/v1/system/metrics` - 系统指标
- `/api/v1/system/info` - 系统信息

### 日志文件
```
logs/
├── app.log          # 应用日志
├── audit.log        # 审计日志
├── access.log       # Nginx 访问日志
└── error.log        # 错误日志
```

### 集成外部监控
```yaml
# Prometheus 配置
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
```

## 🔄 备份和恢复

### 自动备份
```bash
# 使用内置备份脚本
./deploy.sh backup

# 或设置定时任务
crontab -e
# 添加以下行（每天凌晨2点备份）
0 2 * * * cd /path/to/enterprise-data-query && ./deploy.sh backup
```

### 手动备份
```bash
# 备份数据库
docker-compose exec mysql-demo mysqldump -u root -proot test > backup.sql

# 备份应用数据
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ logs/ .env
```

### 恢复数据
```bash
# 恢复数据库
docker-compose exec -T mysql-demo mysql -u root -proot test < backup.sql

# 恢复应用数据
tar -xzf backup.tar.gz
```

## 🚨 故障排除

### 常见问题

#### 1. 应用启动失败
```bash
# 检查日志
docker-compose logs app

# 常见原因：
# - 环境变量未设置
# - 端口被占用
# - 依赖服务未启动
```

#### 2. 数据库连接失败
```bash
# 测试数据库连接
docker-compose exec app python -c "
import mysql.connector
try:
    conn = mysql.connector.connect(
        host='mysql-demo',
        user='root',
        password='root'
    )
    print('连接成功')
except Exception as e:
    print(f'连接失败: {e}')
"
```

#### 3. Redis 连接失败
```bash
# 检查 Redis 状态
docker-compose exec redis redis-cli ping
```

#### 4. API 响应慢
```bash
# 检查系统指标
curl http://localhost:8000/api/v1/system/metrics

# 优化建议：
# - 增加连接池大小
# - 启用查询缓存
# - 优化数据库索引
```

### 调试模式
```bash
# 启用调试模式
export DEBUG=true
export LOG_LEVEL=DEBUG

# 重新启动服务
docker-compose restart app
```

## 📈 性能优化建议

### 1. 数据库优化
```sql
-- 为常用查询字段添加索引
CREATE INDEX idx_users_created ON users(created_at);
CREATE INDEX idx_orders_user_date ON orders(user_id, order_date);
```

### 2. 缓存策略
```python
# 配置缓存过期时间
CACHE_EXPIRE_SECONDS = 300  # 5分钟
QUERY_CACHE_TTL = 3600      # 1小时（频繁查询）
```

### 3. 连接池配置
```python
# 调整连接池大小
CONNECTION_POOL_MAX_SIZE = 50      # 最大连接数
CONNECTION_POOL_IDLE_TIMEOUT = 600 # 空闲超时（秒）
```

### 4. 查询优化
```python
# 启用查询限制
MAX_QUERY_ROWS = 10000      # 单次查询最大行数
QUERY_TIMEOUT_SECONDS = 60  # 查询超时时间
```

## 🔐 安全最佳实践

### 1. 生产环境配置
- 使用强密码和密钥
- 禁用调试模式
- 配置 HTTPS
- 限制 CORS 域名

### 2. 访问控制
- 使用最小权限原则
- 定期轮换密钥
- 启用审计日志
- 实施速率限制

### 3. 数据保护
- 加密敏感数据
- 定期备份
- 监控异常访问
- 实施数据脱敏

## 🤝 贡献指南

### 开发流程
```bash
# 1. 创建开发分支
git checkout -b feature/your-feature

# 2. 运行测试
./start.sh test

# 3. 代码检查
./start.sh lint

# 4. 提交更改
git add .
git commit -m "feat: add your feature"

# 5. 推送分支
git push origin feature/your-feature
```

### 代码规范
- 遵循 PEP 8 规范
- 使用类型注解
- 编写单元测试
- 更新文档

### 提交信息格式
```
类型(范围): 描述

详细说明（可选）

BREAKING CHANGE: 重大变更说明（可选）
```

类型包括：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具

## 📞 支持

### 获取帮助
- 查看 [API 文档](http://localhost:8000/docs)
- 检查 [系统日志](logs/)
- 查阅 [问题跟踪](issues/)

### 报告问题
```bash
# 收集系统信息
curl http://localhost:8000/api/v1/system/info > system_info.json

# 包含以下信息：
# 1. 系统版本
# 2. 错误日志
# 3. 复现步骤
# 4. 期望行为
```

## 📝 更新日志

### v1.0.0 (2024-01-01)
- ✅ 初始版本发布
- ✅ 支持自然语言查询
- ✅ 多数据源连接
- ✅ 完整的 API 接口
- ✅ Docker 容器化部署

## 📄 许可证

MIT License

Copyright (c) 2024 企业级问数系统

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [DeepAgents](https://deepagents.ai/) - AI 代理平台
- 所有贡献者和用户

---

**企业级问数系统** - 让数据查询更智能、更安全、更高效 🚀

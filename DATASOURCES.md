# 数据源支持指南

## 📊 当前支持的数据源

### ✅ 已实现

| 数据源 | 状态 | 连接器 | 说明 |
|-------|------|--------|------|
| **MySQL** | ✅ 已实现 | `MySQLConnector` | 完整支持 |
| **PostgreSQL** | ✅ 已实现 | `PostgreSQLConnector` | 完整支持 |
| **SQLite** | ✅ 基础支持 | `SQLAlchemy` | 通过 SQLAlchemy 支持 |

### ⏳ 计划中

| 数据源 | 优先级 | 预计 | 说明 |
|-------|-------|------|------|
| **ClickHouse** | 🔴 高 | 待开发 | OLAP 分析 |
| **Oracle** | 🟡 中 | 待开发 | 企业数据库 |
| **SQL Server** | 🟡 中 | 待开发 | 微软数据库 |
| **MariaDB** | 🟢 低 | 待开发 | MySQL 兼容 |
| **Snowflake** | 🟡 中 | 待开发 | 云数据仓库 |
| **BigQuery** | 🟡 中 | 待开发 | Google 云 |
| **Redshift** | 🟡 中 | 待开发 | AWS 云 |
| **Doris/StarRocks** | 🟢 低 | 待开发 | 国产 OLAP |

---

## 🔧 已实现的数据源详情

### 1. MySQL

**连接器**: `connectors/mysql.py` - `MySQLConnector`

**支持版本**: MySQL 5.7+, 8.0+

**功能特性**:
- ✅ 连接池管理
- ✅ 自动重连
- ✅ Schema 自动发现
- ✅ 表注释和字段注释
- ✅ 外键关系识别
- ✅ 查询超时控制
- ✅ 流式结果处理

**使用示例**:
```python
from connectors import MySQLConnector

connector = MySQLConnector(
    host="localhost",
    port=3306,
    database="test",
    username="root",
    password="password",
    charset="utf8mb4",
    pool_size=5
)

# 连接
connector.connect()

# 执行查询
data, columns = connector.execute_query(
    "SELECT * FROM users LIMIT 100",
    limit=10000,
    timeout=60
)

# 获取 Schema
schema = connector.get_schema()
print(f"表数量：{len(schema['tables'])}")

# 断开连接
connector.disconnect()
```

**配置示例**:
```python
# 在 .env 或配置文件中
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=test
MYSQL_USERNAME=root
MYSQL_PASSWORD=your_password
```

**依赖**:
```bash
pip install pymysql sqlalchemy
```

---

### 2. PostgreSQL

**连接器**: `connectors/postgresql.py` - `PostgreSQLConnector`

**支持版本**: PostgreSQL 10+, 11+, 12+, 13+, 14+, 15+

**功能特性**:
- ✅ 连接池管理
- ✅ 自动重连
- ✅ Schema 自动发现（支持多 Schema）
- ✅ 表注释和字段注释
- ✅ 外键关系识别
- ✅ 查询超时控制
- ✅ 支持自定义 Schema

**使用示例**:
```python
from connectors import PostgreSQLConnector

connector = PostgreSQLConnector(
    host="localhost",
    port=5432,
    database="test",
    username="postgres",
    password="password",
    schema="public",  # 可选，默认 public
    pool_size=5
)

# 连接
connector.connect()

# 执行查询
data, columns = connector.execute_query(
    "SELECT * FROM users LIMIT 100",
    limit=10000,
    timeout=60
)

# 获取 Schema（包含所有 Schema 的表）
schema = connector.get_schema()
print(f"数据库：{schema['database']}")
print(f"Schema: {schema['schema']}")

# 断开连接
connector.disconnect()
```

**配置示例**:
```python
# 在 .env 或配置文件中
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=test
POSTGRESQL_USERNAME=postgres
POSTGRESQL_PASSWORD=your_password
POSTGRESQL_SCHEMA=public
```

**依赖**:
```bash
pip install psycopg2-binary sqlalchemy
```

---

### 3. SQLite（基础支持）

**说明**: 通过 SQLAlchemy 自动支持

**使用示例**:
```python
from sqlalchemy import create_engine

# 创建 SQLite 连接
engine = create_engine("sqlite:///example.db")

# 可以直接使用，但建议创建专用连接器
```

---

## 🚀 添加新数据源

### 步骤 1: 创建连接器类

继承 `BaseConnector` 并实现必要方法：

```python
# connectors/clickhouse.py
from typing import List, Dict, Any, Tuple, Optional
from .base import BaseConnector

class ClickHouseConnector(BaseConnector):
    """ClickHouse 连接器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9000,
        database: str = "default",
        username: str = "default",
        password: str = "",
        **kwargs
    ):
        super().__init__(host, port, database, username, password, **kwargs)
        self.connection = None
    
    def connect(self) -> bool:
        """建立连接"""
        from clickhouse_driver import Client
        
        self.connection = Client(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.username,
            password=self.password
        )
        self._connected = True
        return True
    
    def disconnect(self):
        """断开连接"""
        if self.connection:
            self.connection.disconnect()
            self.connection = None
            self._connected = False
    
    def execute_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        limit: int = 10000,
        timeout: int = 60
    ) -> Tuple[List[Dict], List[str]]:
        """执行查询"""
        if not self._connected:
            self.connect()
        
        # 添加 LIMIT
        if "LIMIT" not in sql.upper() and sql.strip().upper().startswith("SELECT"):
            sql = f"{sql.rstrip(';')} LIMIT {limit}"
        
        # 执行
        result = self.connection.execute(sql, params or {})
        
        # 获取列名
        columns = [col[0] for col in result.columns]
        
        # 转换为字典列表
        data = [dict(zip(columns, row)) for row in result.result_rows]
        
        return data, columns
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Schema 信息"""
        if not self._connected:
            self.connect()
        
        tables = {}
        
        # 查询表列表
        tables_result = self.connection.execute("""
            SELECT name, engine, comment
            FROM system.tables
            WHERE database = %(database)s
        """, {'database': self.database})
        
        for table_name, engine, comment in tables_result:
            # 获取列信息
            columns_result = self.connection.execute("""
                SELECT name, type, comment
                FROM system.columns
                WHERE database = %(database)s AND table = %(table)s
            """, {'database': self.database, 'table': table_name})
            
            columns = []
            for col_name, col_type, col_comment in columns_result:
                columns.append({
                    "name": col_name,
                    "type": col_type,
                    "description": col_comment or ""
                })
            
            tables[table_name] = {
                "columns": columns,
                "description": comment or "",
                "engine": engine,
                "relationships": []
            }
        
        return {"tables": tables, "database": self.database}
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        if not self._connected:
            self.connect()
        
        result = self.connection.execute("""
            SELECT name FROM system.tables
            WHERE database = %(database)s
        """, {'database': self.database})
        
        return [row[0] for row in result]
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        if not self._connected:
            self.connect()
        
        result = self.connection.execute("""
            SELECT name, type, comment
            FROM system.columns
            WHERE database = %(database)s AND table = %(table)s
        """, {'database': self.database, 'table': table_name})
        
        return [
            {
                "name": col_name,
                "type": col_type,
                "description": col_comment or ""
            }
            for col_name, col_type, col_comment in result
        ]
```

---

### 步骤 2: 注册连接器

更新 `connectors/__init__.py`:

```python
"""数据源连接器模块"""
from .base import BaseConnector
from .mysql import MySQLConnector
from .postgresql import PostgreSQLConnector
from .clickhouse import ClickHouseConnector  # 新增

__all__ = [
    "BaseConnector",
    "MySQLConnector",
    "PostgreSQLConnector",
    "ClickHouseConnector",  # 新增
]
```

---

### 步骤 3: 更新 API 路由

在 `api/routes.py` 的 `get_datasource_connector` 函数中添加：

```python
def get_datasource_connector(
    datasource_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取数据源连接器"""
    datasources = {
        "demo_mysql": {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "test",
            "username": "root",
            "password": "root"
        },
        "demo_pg": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test",
            "username": "postgres",
            "password": "postgres"
        },
        # 新增 ClickHouse
        "demo_clickhouse": {
            "type": "clickhouse",
            "host": "localhost",
            "port": 9000,
            "database": "default",
            "username": "default",
            "password": ""
        }
    }
    
    if datasource_id not in datasources:
        raise HTTPException(404, f"数据源 {datasource_id} 不存在")
    
    config = datasources[datasource_id]
    
    if config["type"] == "mysql":
        return MySQLConnector(**config)
    elif config["type"] == "postgresql":
        return PostgreSQLConnector(**config)
    elif config["type"] == "clickhouse":  # 新增
        return ClickHouseConnector(**config)
    else:
        raise HTTPException(400, f"不支持的数据源类型：{config['type']}")
```

---

### 步骤 4: 添加依赖

在 `requirements.txt` 中添加：

```txt
# ClickHouse
clickhouse-driver>=0.2.0
```

---

## 📝 数据源配置管理

### 数据库配置表（建议实现）

```sql
CREATE TABLE datasources (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- mysql, postgresql, clickhouse, ...
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    database VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    password_encrypted TEXT NOT NULL,  -- 加密存储
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    
    INDEX idx_type (type),
    INDEX idx_status (status)
);
```

### 配置示例

```python
# config/data_sources.py
DATA_SOURCES = {
    "mysql_prod": {
        "type": "mysql",
        "host": "prod-mysql.example.com",
        "port": 3306,
        "database": "production",
        "username": "app_user",
        "password": "${MYSQL_PASSWORD}",  # 从环境变量读取
        "pool_size": 10,
        "ssl": True
    },
    "pg_analytics": {
        "type": "postgresql",
        "host": "pg-analytics.example.com",
        "port": 5432,
        "database": "analytics",
        "username": "analyst",
        "password": "${PG_PASSWORD}",
        "schema": "public",
        "pool_size": 5
    },
    "clickhouse_olap": {
        "type": "clickhouse",
        "host": "clickhouse.example.com",
        "port": 9000,
        "database": "default",
        "username": "default",
        "password": "",
        "compression": True
    }
}
```

---

## 🔐 安全建议

### 1. 密码加密存储

```python
from cryptography.fernet import Fernet

# 加密
cipher = Fernet(secret_key)
encrypted_password = cipher.encrypt(password.encode())

# 解密
decrypted_password = cipher.decrypt(encrypted_password).decode()
```

### 2. 使用环境变量

```bash
# .env
MYSQL_PASSWORD=your_secure_password
PG_PASSWORD=your_secure_password
```

```python
# 代码中
import os
password = os.getenv("MYSQL_PASSWORD")
```

### 3. 连接权限控制

```python
# 为不同用户配置不同的数据源访问权限
USER_DATASOURCE_PERMISSIONS = {
    "admin": ["*"],  # 所有数据源
    "analyst": ["pg_analytics", "clickhouse_olap"],
    "developer": ["mysql_dev"]
}
```

---

## 📊 数据源对比

| 特性 | MySQL | PostgreSQL | ClickHouse |
|-----|-------|-----------|-----------|
| **类型** | 关系型 | 关系型 | OLAP |
| **适用场景** | OLTP | OLTP/OLAP | OLAP |
| **查询性能** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **并发性能** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **数据量** | GB-TB | GB-TB | TB-PB |
| **实时性** | 实时 | 实时 | 近实时 |
| **SQL 支持** | 完整 | 完整 | 部分 |
| **事务支持** | ✅ | ✅ | ❌ |
| **推荐用途** | 业务数据库 | 业务/分析 | 数据分析 |

---

## 🎯 选择建议

### 业务场景推荐

| 场景 | 推荐数据源 | 理由 |
|-----|-----------|------|
| **电商订单系统** | MySQL/PostgreSQL | 事务支持，数据一致性 |
| **用户管理系统** | MySQL/PostgreSQL | 关系复杂，需要事务 |
| **日志分析** | ClickHouse | 海量数据，聚合查询 |
| **实时报表** | ClickHouse | 快速聚合，OLAP 优化 |
| **数据仓库** | PostgreSQL/ClickHouse | 复杂查询，分析能力 |
| **实时大屏** | ClickHouse | 秒级响应，高并发 |

---

## 📈 性能优化建议

### MySQL
```sql
-- 1. 添加索引
CREATE INDEX idx_created_at ON orders(created_at);

-- 2. 使用覆盖索引
SELECT id, created_at FROM orders WHERE created_at > '2024-01-01';

-- 3. 避免 SELECT *
SELECT id, name, status FROM users;
```

### PostgreSQL
```sql
-- 1. 使用 EXPLAIN 分析
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 1;

-- 2. 添加合适索引
CREATE INDEX CONCURRENTLY idx_user_id ON orders(user_id);

-- 3. 使用分区表
CREATE TABLE orders_2024 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### ClickHouse
```sql
-- 1. 使用合适的引擎
CREATE TABLE events (
    event_date Date,
    event_time DateTime,
    event String
) ENGINE = MergeTree()
ORDER BY (event_date, event_time);

-- 2. 使用物化视图
CREATE MATERIALIZED VIEW daily_stats ENGINE = SummingMergeTree()
ORDER BY event_date
AS SELECT 
    toDate(event_time) as event_date,
    count() as event_count
FROM events
GROUP BY event_date;
```

---

## 🔗 相关资源

### 官方文档
- [MySQL](https://dev.mysql.com/doc/)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [ClickHouse](https://clickhouse.com/docs/)

### 相关代码
- `connectors/base.py` - 基础连接器
- `connectors/mysql.py` - MySQL 实现
- `connectors/postgresql.py` - PostgreSQL 实现

---

## ✅ 总结

### 当前支持

| 数据源 | 状态 | 生产可用 |
|-------|------|---------|
| MySQL | ✅ 完整支持 | ✅ 是 |
| PostgreSQL | ✅ 完整支持 | ✅ 是 |
| SQLite | ✅ 基础支持 | ⚠️ 测试用 |

### 推荐添加（按优先级）

1. **ClickHouse** - OLAP 分析场景
2. **Oracle** - 企业客户需求
3. **SQL Server** - 微软生态
4. **Snowflake/BigQuery** - 云原生场景

### 扩展性

系统设计支持轻松添加新数据源：
- ✅ 统一接口 `BaseConnector`
- ✅ 插件式架构
- ✅ 配置驱动
- ✅ 热插拔支持

---

**文档版本**: 1.0  
**最后更新**: 2024

# Oracle 数据源集成指南

## ✅ Oracle 连接器已实现

**文件**: `connectors/oracle.py` - `OracleConnector`

**支持版本**: Oracle Database 11g, 12c, 18c, 19c, 21c

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install oracledb>=1.3.0
```

**注意**: `oracledb` 是 Oracle 官方 Python 驱动，支持 Thin 模式（无需安装 Oracle Client）

---

### 2. 基础使用

```python
from connectors import OracleConnector

# 创建连接器
connector = OracleConnector(
    host="localhost",
    port=1521,
    database="ORCL",        # SID 或服务名
    username="SYSTEM",
    password="your_password",
    schema="SYSTEM",         # Schema 名
    service_name=False,      # False=使用 SID, True=使用服务名
    pool_size=5
)

# 连接
connector.connect()

# 执行查询
data, columns = connector.execute_query(
    "SELECT * FROM employees WHERE ROWNUM <= 100",
    limit=100,
    timeout=60
)

print(f"获取 {len(data)} 行数据")

# 获取 Schema 信息
schema = connector.get_schema()
print(f"表数量：{len(schema['tables'])}")

# 断开连接
connector.disconnect()
```

---

### 3. 连接方式

#### 方式 1: 使用 SID 连接

```python
connector = OracleConnector(
    host="192.168.1.100",
    port=1521,
    database="ORCL",        # SID
    username="scott",
    password="tiger",
    service_name=False      # 使用 SID
)
```

#### 方式 2: 使用服务名连接

```python
connector = OracleConnector(
    host="192.168.1.100",
    port=1521,
    database="pdborcl",     # 服务名
    username="scott",
    password="tiger",
    service_name=True       # 使用服务名
)
```

---

## 📋 功能特性

### ✅ 已实现功能

| 功能 | 说明 | 状态 |
|-----|------|------|
| 连接池管理 | SQLAlchemy 连接池 | ✅ |
| 自动重连 | 连接断开自动重连 | ✅ |
| Schema 发现 | 自动发现表和列 | ✅ |
| 表注释 | 读取表注释 | ✅ |
| 字段注释 | 读取列注释 | ✅ |
| 外键关系 | 识别外键关联 | ✅ |
| 索引信息 | 获取表索引 | ✅ |
| 表统计 | 行数、块数等 | ✅ |
| LOB 处理 | CLOB/BLOB 自动转换 | ✅ |
| 查询限制 | ROWNUM 自动添加 | ✅ |
| 多 Schema | 支持切换 Schema | ✅ |

---

## 🔧 高级用法

### 1. 获取表信息

```python
# 获取所有表
tables = connector.get_tables()
print(f"表列表：{tables}")

# 获取表的列信息
columns = connector.get_table_columns("EMPLOYEES")
for col in columns:
    print(f"{col['name']}: {col['type']} ({'NULL' if col['nullable'] else 'NOT NULL'})")

# 获取表注释
description = connector.get_table_description("EMPLOYEES")
print(f"表注释：{description}")

# 获取外键关系
foreign_keys = connector.get_foreign_keys("ORDERS")
for fk in foreign_keys:
    print(f"{fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}")
```

### 2. 获取完整 Schema

```python
schema = connector.get_schema()

# 访问表信息
for table_name, table_info in schema['tables'].items():
    print(f"\n表：{table_name}")
    print(f"描述：{table_info['description']}")
    
    # 列信息
    for col in table_info['columns']:
        print(f"  - {col['name']}: {col['type']}")
    
    # 外键关系
    for fk in table_info['relationships']:
        print(f"  外键：{fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}")
    
    # 统计信息
    if 'stats' in table_info:
        stats = table_info['stats']
        print(f"  行数：{stats.get('row_count', 'N/A')}")
```

### 3. 处理 LOB 类型

```python
# OracleConnector 自动处理 CLOB/BLOB
data, columns = connector.execute_query("""
    SELECT id, name, resume_clob, photo_blob
    FROM employees
    WHERE ROWNUM <= 10
""")

for row in data:
    # CLOB 字段自动转换为字符串
    resume = row['resume_clob']  # str
    
    # BLOB 字段自动转换为 bytes
    photo = row['photo_blob']    # bytes
```

---

## ⚙️ 配置选项

### 连接参数

```python
OracleConnector(
    # 基础参数
    host="localhost",           # 主机地址
    port=1521,                  # 端口（默认 1521）
    database="ORCL",            # SID 或服务名
    username="SYSTEM",          # 用户名
    password="password",        # 密码
    
    # Oracle 特定参数
    schema="SYSTEM",            # Schema 名（默认与用户名相同）
    service_name=False,         # True=使用服务名，False=使用 SID
    encoding="UTF-8",           # 字符编码
    pool_size=5,                # 连接池大小
    
    # 高级参数
    threaded=True,              # 多线程支持
    events=True,                # 事件通知
    purity=0                    # 连接纯度
)
```

---

## 🔐 安全建议

### 1. 使用环境变量存储密码

```bash
# .env
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_DATABASE=ORCL
ORACLE_USERNAME=scott
ORACLE_PASSWORD=your_secure_password
```

```python
# 代码中
import os

connector = OracleConnector(
    host=os.getenv("ORACLE_HOST"),
    database=os.getenv("ORACLE_DATABASE"),
    username=os.getenv("ORACLE_USERNAME"),
    password=os.getenv("ORACLE_PASSWORD")
)
```

### 2. 使用只读账号

```sql
-- 创建只读用户
CREATE USER reader IDENTIFIED BY strong_password;
GRANT CONNECT TO reader;
GRANT SELECT ON scott.employees TO reader;
GRANT SELECT ON scott.departments TO reader;
```

### 3. 启用 SSL 连接

```python
connector = OracleConnector(
    host="oracle.example.com",
    database="prod_db",
    username="app_user",
    password="password",
    # SSL 配置
    ssl=True,
    ssl_verify="FULL"  # NONE, OPTIONAL, FULL
)
```

---

## 📊 Oracle 数据字典查询

### 常用数据字典视图

```python
# 查询所有表
connector.execute_query("""
    SELECT table_name, num_rows, last_analyzed
    FROM all_tables
    WHERE owner = 'SCOTT'
""")

# 查询所有列
connector.execute_query("""
    SELECT table_name, column_name, data_type, data_length, nullable
    FROM all_tab_columns
    WHERE owner = 'SCOTT'
    ORDER BY table_name, column_id
""")

# 查询所有索引
connector.execute_query("""
    SELECT table_name, index_name, uniqueness, status
    FROM all_indexes
    WHERE owner = 'SCOTT'
""")

# 查询外键关系
connector.execute_query("""
    SELECT 
        a.table_name,
        a.column_name,
        c_pk.table_name AS pk_table,
        b.column_name AS pk_column
    FROM all_cons_columns a
    JOIN all_constraints c ON a.constraint_name = c.constraint_name
    JOIN all_cons_columns b ON c.r_constraint_name = b.constraint_name
    WHERE c.constraint_type = 'R'
      AND a.owner = 'SCOTT'
""")
```

---

## 🐛 常见问题

### 1. 连接失败：ORA-12162

**错误**: `ORA-12162: TNS:net service name is incorrectly specified`

**解决**: 明确指定使用 SID 还是服务名

```python
# 使用 SID
connector = OracleConnector(
    database="ORCL",
    service_name=False  # 明确指定
)

# 使用服务名
connector = OracleConnector(
    database="pdborcl",
    service_name=True   # 明确指定
)
```

---

### 2. 中文乱码

**解决**: 设置正确的编码

```python
connector = OracleConnector(
    encoding="UTF-8",
    nencoding="UTF-8"
)
```

确保数据库字符集支持中文：
```sql
SELECT * FROM nls_database_parameters 
WHERE parameter IN ('NLS_CHARACTERSET', 'NLS_NCHAR_CHARACTERSET');
```

---

### 3. LOB 字段读取失败

**解决**: 连接器已自动处理 LOB，但如果遇到问题：

```python
from cx_Oracle import DB_TYPE_CLOB, DB_TYPE_BLOB

# 手动处理 LOB
data, columns = connector.execute_query("SELECT id, resume FROM employees")
for row in data:
    if hasattr(row['resume'], 'read'):
        row['resume'] = row['resume'].read()
```

---

### 4. 查询性能慢

**优化建议**:

1. **使用索引**
```sql
CREATE INDEX idx_emp_dept ON employees(department_id);
```

2. **使用绑定变量**
```python
# ✅ 推荐
connector.execute_query(
    "SELECT * FROM employees WHERE department_id = :dept_id",
    params={"dept_id": 10}
)

# ❌ 不推荐
connector.execute_query(
    f"SELECT * FROM employees WHERE department_id = {dept_id}"
)
```

3. **添加 ROWNUM 限制**
```python
# OracleConnector 会自动添加，但也可以手动添加
connector.execute_query(
    "SELECT * FROM employees WHERE ROWNUM <= 1000"
)
```

---

## 📈 性能优化

### 1. 连接池配置

```python
connector = OracleConnector(
    pool_size=10,        # 基础连接数
    max_overflow=20,     # 最大溢出连接
    pool_recycle=3600,   # 1 小时回收
    pool_pre_ping=True   # 健康检查
)
```

### 2. 批量查询

```python
# 分批获取大数据
offset = 0
batch_size = 1000

while True:
    data, _ = connector.execute_query(f"""
        SELECT * FROM (
            SELECT t.*, ROWNUM rnum FROM (
                SELECT * FROM large_table ORDER BY id
            ) t WHERE ROWNUM <= {offset + batch_size}
        ) WHERE rnum > {offset}
    """)
    
    if not data:
        break
    
    process(data)
    offset += batch_size
```

---

## 🔄 在 API 中使用

### 配置数据源

在 `api/routes.py` 中添加：

```python
def get_datasource_connector(
    datasource_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取数据源连接器"""
    datasources = {
        "oracle_prod": {
            "type": "oracle",
            "host": "oracle.example.com",
            "port": 1521,
            "database": "PROD",
            "username": "app_user",
            "password": os.getenv("ORACLE_PASSWORD"),
            "schema": "APP_SCHEMA",
            "service_name": True
        },
        # ... 其他数据源
    }
    
    config = datasources[datasource_id]
    
    if config["type"] == "oracle":
        return OracleConnector(**config)
    # ... 其他类型
```

### API 调用示例

```bash
# 查询 Oracle 数据
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "natural_query": "查询所有员工",
    "datasource_id": "oracle_prod",
    "limit": 100
  }'
```

---

## 📝 依赖说明

### requirements.txt

```txt
oracledb>=1.3.0  # Oracle 官方驱动
sqlalchemy>=2.0.0
```

### 安装

```bash
# 基础安装（Thin 模式，无需 Oracle Client）
pip install oracledb

# 完整安装（需要 Oracle Client，支持更多功能）
pip install oracledb --config-settings=mode=thick
```

---

## ✅ 总结

### Oracle 连接器特性

| 特性 | 说明 |
|-----|------|
| **驱动** | oracledb (Thin 模式) |
| **连接方式** | SID / 服务名 |
| **字符集** | UTF-8 支持 |
| **LOB 处理** | CLOB/BLOB 自动转换 |
| **查询限制** | ROWNUM 自动添加 |
| **Schema** | 多 Schema 支持 |
| **性能** | 连接池 + 流式查询 |

### 使用建议

1. ✅ 使用环境变量存储敏感信息
2. ✅ 使用只读账号进行查询
3. ✅ 添加 ROWNUM 限制防止大数据
4. ✅ 使用连接池提高性能
5. ✅ 处理 LOB 字段时注意内存

---

**文档版本**: 1.0  
**最后更新**: 2024

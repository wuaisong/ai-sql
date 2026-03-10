# 快速启动指南

## 🚀 5 分钟快速开始

### 1. 安装依赖

```bash
cd enterprise-data-query
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 基础配置
APP_NAME=Enterprise Data Query System
DEBUG=True
PORT=8000

# DeepAgents 配置（可选，不配置则使用模拟模式）
DEEPAGENTS_MODEL=gpt-4
DEEPAGENTS_API_KEY=your-api-key-here

# 安全配置（生产环境务必修改）
SECRET_KEY=change-this-to-a-random-secret-key
```

### 3. 运行示例（推荐先测试）

```bash
python examples.py
```

你会看到 5 个示例的输出：
- ✅ 基础 AI 代理使用
- ✅ SQL 生成、验证和优化
- ✅ 代理池使用
- ✅ 完整查询流程
- ✅ 数据库连接器

### 4. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动

### 5. 访问 API 文档

打开浏览器访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 📝 API 使用示例

### 1. 登录获取 Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "username": "admin",
  "role": "admin"
}
```

### 2. 执行自然语言查询

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "natural_query": "统计最近 30 天的销售趋势",
    "datasource_id": "demo_mysql",
    "use_cache": true,
    "limit": 1000
  }'
```

响应：
```json
{
  "success": true,
  "data": [...],
  "columns": ["date", "total_sales", "order_count"],
  "row_count": 30,
  "sql": "SELECT DATE(created_at) as date, SUM(amount)...",
  "explanation": "查询最近 30 天的销售统计",
  "execution_time_ms": 125.5,
  "confidence": 0.85,
  "from_cache": false
}
```

### 3. 获取数据源 Schema

```bash
curl -X GET http://localhost:8000/api/v1/datasources/demo_mysql/schema \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

---

## 🧪 测试用户

系统预置了 3 个测试用户：

| 用户名 | 密码 | 角色 | 权限 |
|-------|------|------|------|
| admin | admin123 | admin | read, write, admin |
| analyst | analyst123 | analyst | read, write |
| viewer | viewer123 | viewer | read |

---

## 📂 项目结构速览

```
enterprise-data-query/
├── core/              # 核心引擎 ⭐
│   ├── agent.py       # AI 代理（756 行）
│   ├── query_processor.py  # 查询管道（896 行）
│   └── sql_generator.py    # SQL 处理（865 行）
├── connectors/        # 数据库连接器
├── services/          # 业务服务
├── api/               # API 接口
├── main.py            # 入口文件
├── examples.py        # 使用示例
└── README.md          # 详细文档
```

---

## 🔧 常用操作

### 查看系统状态

```bash
curl http://localhost:8000/api/v1/system/info
```

### 清除缓存

```bash
curl -X POST http://localhost:8000/api/v1/system/clear-cache \
  -H "Authorization: Bearer ..."
```

### 重新加载 Schema

```bash
curl -X POST "http://localhost:8000/api/v1/system/reload-schema?datasource_id=demo_mysql" \
  -H "Authorization: Bearer ..."
```

---

## ⚠️ 常见问题

### Q: 没有 DeepAgents API Key 能用吗？

A: 可以！系统会自动切换到模拟模式，使用规则和模板生成 SQL。

### Q: 如何连接自己的数据库？

A: 
1. 在 `api/routes.py` 中修改 `get_datasource_connector` 函数
2. 添加你的数据库配置
3. 重启服务

### Q: 如何修改 AI 模型？

A: 修改 `.env` 中的 `DEEPAGENTS_MODEL` 变量：
```env
DEEPAGENTS_MODEL=claude-3-sonnet
```

### Q: 查询太慢怎么办？

A: 
1. 启用缓存（默认已启用）
2. 添加数据库索引
3. 限制查询行数（使用 `limit` 参数）
4. 检查 SQL 优化建议

---

## 📚 深入学习

1. **阅读文档**
   - `README.md` - 项目说明
   - `ARCHITECTURE.md` - 架构设计
   - `PROJECT_SUMMARY.md` - 功能总结

2. **运行示例**
   - `python examples.py` - 查看 5 个完整示例

3. **研究代码**
   - `core/agent.py` - AI 代理引擎
   - `core/query_processor.py` - 查询处理管道
   - `core/sql_generator.py` - SQL 生成/验证/优化

4. **自定义扩展**
   - 添加新的数据源连接器
   - 自定义意图识别规则
   - 扩展 SQL 模板库

---

## 🎯 下一步

- [ ] 配置你的数据库连接
- [ ] 测试自然语言查询
- [ ] 查看 API 文档了解所有端点
- [ ] 阅读架构文档理解系统设计
- [ ] 根据需求自定义功能

---

**祝你使用愉快！** 🚀

如有问题，请查阅文档或查看 `examples.py` 中的示例代码。

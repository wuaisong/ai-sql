# DeepAgents 集成更新说明

## ✅ 已完成集成

### 使用官方 `create_deep_agent` API

已将 `core/agent.py` 更新为使用 LangChain DeepAgents 官方的 `create_deep_agent` 函数。

## 📋 API 变更对比

### ❌ 旧实现（已废弃）
```python
from deepagents import Agent, Task

agent = Agent(
    model=self.config.model,
    api_key=self.config.api_key,
    temperature=self.config.temperature
)

task = Task(
    description=prompt,
    json_mode=self.config.enable_json_mode
)

response = agent.execute(task)
```

### ✅ 新实现（当前使用）
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[custom_tool1, custom_tool2],
    system_prompt="你是专业的 SQL 专家...",
    middleware=(),
    subagents=None,
    skills=None,
    memory=None,
    backend=None,
    checkpointer=None,
    store=None,
    interrupt_on=None,
    debug=False,
    cache=None,
    response_format=None,
)

# 调用
result = agent.invoke({"messages": [{"role": "user", "content": "查询用户数据"}]})
```

## 🔧 核心变更

### 1. Agent 创建方式
- **旧**: `Agent()` 类实例化
- **新**: `create_deep_agent()` 工厂函数

### 2. 调用方式
- **旧**: `agent.execute(task)`
- **新**: `agent.invoke({"messages": [...]})`

### 3. 工具集成
- **旧**: 无内置工具支持
- **新**: 支持自定义工具列表，内置 `write_todos`, `ls`, `read_file`, `write_file`, `task` 等

### 4. 中间件系统
- **旧**: 无
- **新**: 支持完整中间件栈（TodoList, Filesystem, SubAgent, Summarization 等）

### 5. 后端支持
- **旧**: 无
- **新**: 支持可插拔后端（StateBackend, FilesystemBackend, StoreBackend 等）

### 6. 子代理
- **旧**: 无
- **新**: 支持子代理 spawning 和任务委托

### 7. 内存和持久化
- **旧**: 简单内存缓存
- **新**: 支持 AGENTS.md 文件内存、跨线程持久化

## 📦 依赖要求

```bash
pip install deepagents>=0.4.0
```

## 🚀 使用示例

### 基础用法
```python
from core.agent import create_agent

# 创建 SQL 专家代理
agent = create_agent(
    model="claude-sonnet-4-6",
    role="sql_expert"
)

# 设置 schema
agent.set_schema_context({
    "tables": {
        "users": {
            "columns": [
                {"name": "id", "type": "INT"},
                {"name": "username", "type": "VARCHAR"}
            ]
        }
    }
})

# 生成 SQL
result = agent.generate_sql("查询所有用户")
print(result.sql)
```

### 高级用法（自定义工具和中间件）
```python
from deepagents import create_deep_agent
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取天气"""
    return f"It's sunny in {city}"

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="你是 helpful assistant",
    skills=["/skills/user/"],
    memory=["/memory/AGENTS.md"],
    debug=True
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "北京的天气如何？"}]
})
```

## 🎯 DeepAgents 内置能力

使用 `create_deep_agent` 创建的代理自动拥有以下能力：

### 内置工具
1. **write_todos** - 任务规划和分解
2. **ls, read_file, write_file, edit_file, glob, grep** - 文件操作
3. **execute** - 执行 shell 命令（需要 sandbox 后端）
4. **task** - 调用子代理

### 中间件栈（按顺序应用）
1. TodoListMiddleware - 待办事项管理
2. FilesystemMiddleware - 文件系统工具
3. SubAgentMiddleware - 子代理支持
4. SummarizationMiddleware - 对话摘要
5. AnthropicPromptCachingMiddleware - Prompt 缓存
6. PatchToolCallsMiddleware - 工具调用修复

### 后端选项
- **StateBackend** - 内存存储（默认）
- **FilesystemBackend** - 本地文件系统
- **StoreBackend** - LangGraph 持久化存储
- **Sandbox 后端** - Modal, Daytona, Deno 隔离执行

## 📊 性能优势

| 特性 | 旧实现 | 新实现 (create_deep_agent) |
|-----|-------|---------------------------|
| 任务规划 | ❌ | ✅ write_todos 工具 |
| 文件操作 | ❌ | ✅ 内置文件系统 |
| 子代理 | ❌ | ✅ task 工具 |
| 持久化 | ❌ | ✅ 多后端支持 |
| 中间件 | ❌ | ✅ 完整中间件栈 |
| 技能系统 | ❌ | ✅ AGENTS.md 技能 |
| 人工审核 | ❌ | ✅ interrupt_on |

## ⚠️ 注意事项

1. **模型默认值**: 新实现默认使用 `claude-sonnet-4-6`，旧实现需要显式指定
2. **API Key**: 通过环境变量 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` 提供
3. **响应格式**: 新实现使用 LangChain 消息格式，需要适配解析逻辑
4. **工具定义**: 自定义工具需要使用 `@tool` 装饰器或符合 LangChain 工具规范

## 🔗 相关文档

- [DeepAgents 官方文档](https://docs.langchain.com/oss/python/deepagents)
- [API Reference](https://reference.langchain.com/python/deepagents/graph/create_deep_agent)
- [Quickstart](https://docs.langchain.com/oss/python/deepagents/quickstart)
- [Customization](https://docs.langchain.com/oss/python/deepagents/customization)

## 📝 下一步

1. ✅ 集成 `create_deep_agent` API
2. ⏳ 添加更多自定义工具（SQL 生成相关）
3. ⏳ 实现 FilesystemBackend 用于 schema 持久化
4. ⏳ 配置子代理用于专业查询
5. ⏳ 添加人工审核流程（interrupt_on）

---

**更新时间**: 2024
**版本**: 1.0.0

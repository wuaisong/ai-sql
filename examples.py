"""
企业级问数系统 - 使用示例
"""
import asyncio
from core.agent import DataQueryAgent, AgentConfig, AgentRole, AgentPool
from core.query_processor import QueryProcessor, QueryContext
from core.sql_generator import SQLGenerator, SQLValidator, SQLOptimizer
from connectors.mysql import MySQLConnector
from services.cache import cache_service


# ============ 示例 1: 基础 AI 代理使用 ============

async def example_agent_basic():
    """基础 AI 代理使用示例"""
    print("=" * 60)
    print("示例 1: 基础 AI 代理使用")
    print("=" * 60)
    
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
    schema_info = {
        "database": "ecommerce",
        "tables": {
            "users": {
                "description": "用户信息表",
                "columns": [
                    {"name": "id", "type": "INT", "description": "用户 ID", "primary_key": True},
                    {"name": "username", "type": "VARCHAR(50)", "description": "用户名"},
                    {"name": "email", "type": "VARCHAR(100)", "description": "邮箱"},
                    {"name": "created_at", "type": "DATETIME", "description": "创建时间"},
                    {"name": "status", "type": "TINYINT", "description": "状态：1-活跃，0-禁用"}
                ]
            },
            "orders": {
                "description": "订单表",
                "columns": [
                    {"name": "id", "type": "INT", "description": "订单 ID", "primary_key": True},
                    {"name": "user_id", "type": "INT", "description": "用户 ID"},
                    {"name": "amount", "type": "DECIMAL(10,2)", "description": "订单金额"},
                    {"name": "status", "type": "TINYINT", "description": "订单状态"},
                    {"name": "created_at", "type": "DATETIME", "description": "下单时间"}
                ],
                "relationships": [
                    "user_id -> users.id"
                ]
            },
            "products": {
                "description": "商品表",
                "columns": [
                    {"name": "id", "type": "INT", "description": "商品 ID"},
                    {"name": "name", "type": "VARCHAR(200)", "description": "商品名称"},
                    {"name": "price", "type": "DECIMAL(10,2)", "description": "价格"},
                    {"name": "stock", "type": "INT", "description": "库存"}
                ]
            }
        }
    }
    
    agent.set_schema_context(schema_info)
    
    # 测试查询
    queries = [
        "查询所有活跃用户",
        "统计最近 30 天的订单总数",
        "显示销售排名前 10 的商品",
        "查询每个用户的订单数量",
        "分析最近半年的销售趋势"
    ]
    
    for query in queries:
        print(f"\n用户查询：{query}")
        result = agent.generate_sql(query)
        
        if result.success:
            print(f"✅ SQL: {result.sql[:200]}")
            print(f"📊 置信度：{result.confidence:.2f}")
            print(f"📝 说明：{result.explanation}")
            if result.tables_used:
                print(f"📋 使用表：{', '.join(result.tables_used)}")
        else:
            print(f"❌ 失败：{result.error}")
        
        print("-" * 60)
    
    # 查看代理指标
    metrics = agent.get_metrics()
    print(f"\n代理性能指标：")
    print(f"  总请求数：{metrics['total_requests']}")
    print(f"  成功率：{metrics['success_rate']:.2%}")
    print(f"  平均响应时间：{metrics['avg_response_time_ms']:.2f}ms")
    print(f"  缓存命中率：{metrics['cache_hit_rate']:.2%}")


# ============ 示例 2: SQL 生成、验证和优化 ============

async def example_sql_pipeline():
    """SQL 处理管道示例"""
    print("\n" + "=" * 60)
    print("示例 2: SQL 生成、验证和优化")
    print("=" * 60)
    
    # 创建组件
    generator = SQLGenerator()
    validator = SQLValidator()
    optimizer = SQLOptimizer()
    
    # 设置 schema
    schema_info = {
        "tables": {
            "users": {
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "username", "type": "VARCHAR"},
                    {"name": "email", "type": "VARCHAR"}
                ]
            }
        }
    }
    
    generator.set_schema_context(schema_info)
    validator.set_schema_context(schema_info)
    optimizer.set_schema_context(schema_info)
    
    # 测试查询
    query = "查询所有用户，按注册时间降序排列"
    print(f"\n用户查询：{query}")
    
    # 1. 生成 SQL
    print("\n[1] 生成 SQL...")
    gen_result = generator.generate_sql(query)
    print(f"    SQL: {gen_result.sql}")
    print(f"    置信度：{gen_result.confidence}")
    
    # 2. 验证 SQL
    print("\n[2] 验证 SQL...")
    val_result = validator.validate(gen_result.sql)
    print(f"    是否有效：{val_result.is_valid}")
    print(f"    风险等级：{val_result.risk_level}")
    if val_result.issues:
        print(f"    问题：{val_result.issues}")
    if val_result.warnings:
        print(f"    警告：{val_result.warnings}")
    
    # 3. 优化 SQL
    print("\n[3] 优化 SQL...")
    opt_result = optimizer.optimize(val_result.sql)
    print(f"    优化后：{opt_result.optimized_sql}")
    print(f"    性能提升：{opt_result.estimated_performance_gain}")
    if opt_result.index_suggestions:
        print(f"    索引建议：{opt_result.index_suggestions}")
    if opt_result.rewrite_suggestions:
        print(f"    重写建议：{opt_result.rewrite_suggestions}")


# ============ 示例 3: 代理池使用 ============

async def example_agent_pool():
    """代理池使用示例"""
    print("\n" + "=" * 60)
    print("示例 3: 代理池使用")
    print("=" * 60)
    
    # 创建代理池
    pool = AgentPool(max_agents=5)
    
    # 添加不同角色的代理
    configs = [
        AgentConfig(model="gpt-4", role=AgentRole.SQL_EXPERT, temperature=0.1),
        AgentConfig(model="gpt-4", role=AgentRole.DATA_ANALYST, temperature=0.2),
        AgentConfig(model="gpt-4", role=AgentRole.QUERY_OPTIMIZER, temperature=0.0),
    ]
    
    for config in configs:
        pool.add_agent(config)
    
    print(f"\n代理池状态：")
    metrics = pool.get_pool_metrics()
    print(f"  总代理数：{metrics['total_agents']}")
    print(f"  空闲代理：{metrics['idle_agents']}")
    print(f"  忙碌代理：{metrics['busy_agents']}")
    
    # 获取可用代理
    agent = pool.get_available_agent()
    if agent:
        print(f"\n获取到代理：{agent.config.role}")
        
        # 广播 schema 更新
        pool.broadcast_schema_update({"database": "test"})
        print("已广播 schema 更新到所有代理")
        
        # 清除所有缓存
        pool.clear_all_caches()
        print("已清除所有代理缓存")


# ============ 示例 4: 完整查询流程 ============

async def example_full_query():
    """完整查询流程示例"""
    print("\n" + "=" * 60)
    print("示例 4: 完整查询流程")
    print("=" * 60)
    
    # 创建查询处理器
    generator = SQLGenerator()
    validator = SQLValidator()
    optimizer = SQLOptimizer()
    
    processor = QueryProcessor(
        sql_generator=generator,
        sql_validator=validator,
        sql_optimizer=optimizer,
        cache_service=cache_service
    )
    
    # 设置 schema
    schema_info = {
        "database": "ecommerce",
        "tables": {
            "orders": {
                "description": "订单表",
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "user_id", "type": "INT"},
                    {"name": "amount", "type": "DECIMAL"},
                    {"name": "created_at", "type": "DATETIME"}
                ]
            }
        }
    }
    processor.set_schema_context(schema_info)
    
    # 处理查询
    query = "统计最近 7 天的每日订单数量和总金额"
    print(f"\n用户查询：{query}")
    
    result = await processor.process_query(
        natural_query=query,
        user_id="demo_user",
        datasource_id="demo_mysql"
    )
    
    print(f"\n处理结果：")
    print(f"  成功：{result.success}")
    print(f"  SQL: {result.sql}")
    print(f"  执行时间：{result.execution_time_ms:.2f}ms")
    
    if result.metadata:
        print(f"  总处理时间：{result.metadata.get('total_processing_time_ms', 0):.2f}ms")
        print(f"  来自缓存：{result.metadata.get('from_cache', False)}")
    
    # 查看处理器统计
    stats = processor.get_stats()
    print(f"\n处理器统计：")
    print(f"  总查询数：{stats['total_queries']}")
    print(f"  成功率：{stats['success_rate']:.2%}")
    print(f"  平均处理时间：{stats['avg_processing_time_ms']:.2f}ms")
    print(f"  缓存命中：{stats['cache_hits']}")


# ============ 示例 5: 数据库连接器 ============

async def example_connector():
    """数据库连接器示例"""
    print("\n" + "=" * 60)
    print("示例 5: 数据库连接器")
    print("=" * 60)
    
    try:
        # 创建 MySQL 连接器
        connector = MySQLConnector(
            host="localhost",
            port=3306,
            database="test",
            username="root",
            password="root"
        )
        
        # 测试连接
        print("\n测试连接...")
        if connector.test_connection():
            print("✅ 连接成功")
        else:
            print("❌ 连接失败")
            return
        
        # 获取表列表
        print("\n获取表列表...")
        tables = connector.get_tables()
        print(f"  表数量：{len(tables)}")
        for table in tables[:5]:
            print(f"    - {table}")
        
        # 获取 schema
        print("\n获取 Schema...")
        schema = connector.get_schema()
        print(f"  数据库：{schema.get('database')}")
        print(f"  表数量：{len(schema.get('tables', {}))}")
        
        # 执行查询
        print("\n执行查询...")
        data, columns = connector.execute_query("SELECT 1 as test")
        print(f"  结果：{data}")
        print(f"  列：{columns}")
        
    except Exception as e:
        print(f"连接器示例需要实际的数据库连接，当前错误：{e}")
        print("这是一个示例，实际使用时请配置正确的数据库信息")


# ============ 主函数 ============

async def main():
    """运行所有示例"""
    print("\n" + "🚀" * 30)
    print("企业级问数系统 - 使用示例")
    print("🚀" * 30 + "\n")
    
    # 运行示例
    await example_agent_basic()
    await example_sql_pipeline()
    await example_agent_pool()
    await example_full_query()
    await example_connector()
    
    print("\n" + "✅" * 30)
    print("所有示例运行完成！")
    print("✅" * 30 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

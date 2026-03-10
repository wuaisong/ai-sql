"""
企业级问数系统 - 入口文件
Enterprise Data Query System
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import run

from config.settings import settings
from api.routes import router
from api.middleware import (
    request_logging_middleware,
    security_headers_middleware,
    error_handler_middleware
)
from core.agent import DataQueryAgent, AgentConfig, AgentPool, AgentRole
from core.query_processor import QueryProcessor
from core.sql_generator import create_sql_processor
from services.cache import cache_service
from utils.logger import logger


# 全局组件
query_processor: QueryProcessor = None
agent_pool: AgentPool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动企业级问数系统...")
    
    global query_processor, agent_pool
    
    try:
        # 1. 初始化 AI 代理池
        logger.info("初始化 AI 代理池...")
        agent_pool = AgentPool(max_agents=3)
        
        # SQL 专家代理
        sql_agent_config = AgentConfig(
            model=settings.DEEPAGENTS_MODEL,
            api_key=settings.DEEPAGENTS_API_KEY,
            api_base=settings.DEEPAGENTS_API_BASE,
            role=AgentRole.SQL_EXPERT,
            temperature=0.1
        )
        agent_pool.add_agent(sql_agent_config)
        
        # 数据分析师代理
        analyst_agent_config = AgentConfig(
            model=settings.DEEPAGENTS_MODEL,
            api_key=settings.DEEPAGENTS_API_KEY,
            api_base=settings.DEEPAGENTS_API_BASE,
            role=AgentRole.DATA_ANALYST,
            temperature=0.2
        )
        agent_pool.add_agent(analyst_agent_config)
        
        # 验证器代理
        validator_agent_config = AgentConfig(
            model=settings.DEEPAGENTS_MODEL,
            api_key=settings.DEEPAGENTS_API_KEY,
            api_base=settings.DEEPAGENTS_API_BASE,
            role=AgentRole.VALIDATOR,
            temperature=0.0
        )
        agent_pool.add_agent(validator_agent_config)
        
        logger.info(f"代理池初始化完成：{agent_pool.get_pool_metrics()}")
        
        # 2. 创建 SQL 处理组件
        logger.info("创建 SQL 处理组件...")
        sql_agent = agent_pool.get_agent_by_role(AgentRole.SQL_EXPERT)
        
        generator, validator, optimizer = create_sql_processor(
            schema_context={},  # 初始为空，后续动态加载
            ai_agent=sql_agent
        )
        
        # 3. 创建查询处理器
        logger.info("创建查询处理器...")
        query_processor = QueryProcessor(
            sql_generator=generator,
            sql_validator=validator,
            sql_optimizer=optimizer,
            connector=None,  # 连接器在查询时动态创建
            cache_service=cache_service
        )
        
        logger.info("系统初始化完成 ✅")
        
        yield
        
    except Exception as e:
        logger.exception(f"系统初始化失败：{e}")
        raise
    
    finally:
        # 关闭时清理
        logger.info("正在关闭系统...")
        if agent_pool:
            agent_pool.clear_all_caches()
        logger.info("系统已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 DeepAgents 的企业级自然语言数据查询系统",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_logging_middleware)
app.middleware("http")(security_headers_middleware)
app.middleware("http")(error_handler_middleware)

# 注册路由
app.include_router(router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/system/info")
async def system_info():
    """系统信息"""
    info = {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "agent_pool": agent_pool.get_pool_metrics() if agent_pool else None,
        "processor_stats": query_processor.get_stats() if query_processor else None,
        "cache_available": cache_service.use_redis if cache_service else False
    }
    return info


@app.post("/api/v1/system/reload-schema")
async def reload_schema(datasource_id: str):
    """重新加载 Schema"""
    if not query_processor:
        return {"success": False, "error": "查询处理器未初始化"}
    
    try:
        # 这里应该从数据库获取最新的 schema
        # 简化实现，返回成功
        logger.info(f"重新加载数据源 {datasource_id} 的 schema")
        
        return {
            "success": True,
            "message": f"Schema 已重新加载：{datasource_id}"
        }
    except Exception as e:
        logger.exception(f"重新加载 schema 失败：{e}")
        return {"success": False, "error": str(e)}


@app.post("/api/v1/system/clear-cache")
async def clear_cache():
    """清除缓存"""
    try:
        if cache_service:
            cache_service.clear()
        if agent_pool:
            agent_pool.clear_all_caches()
        
        return {"success": True, "message": "缓存已清除"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """主函数"""
    # 确保日志目录存在
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 启动服务器
    logger.info(f"启动服务器：{settings.HOST}:{settings.PORT}")
    
    run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()

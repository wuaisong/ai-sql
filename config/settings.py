"""
系统配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """系统配置"""
    
    # 应用配置
    APP_NAME: str = "Enterprise Data Query System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API 配置
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置 (系统元数据)
    META_DB_URL: str = "sqlite:///./meta.db"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # 数据源配置
    DATA_SOURCES: List[dict] = []
    
    # DeepAgents 配置
    DEEPAGENTS_MODEL: str = "gpt-4"
    DEEPAGENTS_API_KEY: Optional[str] = None
    DEEPAGENTS_API_BASE: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # 查询限制
    MAX_QUERY_ROWS: int = 10000
    QUERY_TIMEOUT_SECONDS: int = 60
    CACHE_EXPIRE_SECONDS: int = 300
    
    # 审计配置
    AUDIT_ENABLED: bool = True
    AUDIT_LOG_FILE: str = "logs/audit.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()

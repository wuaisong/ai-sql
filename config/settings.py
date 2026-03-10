"""
系统配置管理
增强安全性验证
"""
import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """系统配置"""
    
    # 应用配置
    APP_NAME: str = "Enterprise Data Query System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # API 配置
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8000, ge=1, le=65535)
    
    # 安全配置
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
        min_length=32,
        description="JWT 密钥，生产环境必须设置"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    
    # 数据库配置 (系统元数据)
    META_DB_URL: str = Field(
        default="sqlite:///./meta.db",
        description="元数据数据库连接字符串"
    )
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_DB: int = Field(default=0, ge=0, le=15)
    REDIS_PASSWORD: Optional[str] = None
    
    # 连接池配置
    CONNECTION_POOL_MAX_SIZE: int = Field(default=20, ge=1, le=100)
    CONNECTION_POOL_IDLE_TIMEOUT: int = Field(default=300, ge=60, le=3600)
    
    # DeepAgents 配置
    DEEPAGENTS_MODEL: str = "gpt-4"
    DEEPAGENTS_API_KEY: Optional[str] = Field(
        default=None,
        description="DeepAgents API 密钥"
    )
    DEEPAGENTS_API_BASE: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FILE: str = "logs/app.log"
    
    # 查询限制
    MAX_QUERY_ROWS: int = Field(default=10000, ge=100, le=1000000)
    QUERY_TIMEOUT_SECONDS: int = Field(default=60, ge=1, le=300)
    CACHE_EXPIRE_SECONDS: int = Field(default=300, ge=60, le=86400)
    
    # 审计配置
    AUDIT_ENABLED: bool = True
    AUDIT_LOG_FILE: str = "logs/audit.log"
    
    # 安全增强
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=6, le=128)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, ge=1, le=1000)
    
    # CORS 配置（生产环境应限制）
    CORS_ALLOW_ORIGINS: List[str] = Field(default=["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外字段
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        """验证 SECRET_KEY"""
        if v == "your-secret-key-change-in-production":
            raise ValueError(
                "必须设置 SECRET_KEY 环境变量，"
                "可以使用命令生成: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v
    
    @validator("DEBUG")
    def validate_debug_mode(cls, v, values):
        """验证调试模式"""
        if v and values.get("SECRET_KEY", "").startswith("dev-"):
            print("⚠️  警告：调试模式下使用开发密钥")
        return v
    
    @validator("CORS_ALLOW_ORIGINS")
    def validate_cors_origins(cls, v, values):
        """验证 CORS 配置"""
        if values.get("DEBUG", False):
            return v  # 调试模式允许所有
        
        if "*" in v and not values.get("DEBUG", False):
            print("⚠️  警告：生产环境 CORS 允许所有来源，建议配置具体域名")
        
        return v
    
    @validator("DEEPAGENTS_API_KEY")
    def validate_api_key(cls, v, values):
        """验证 API 密钥"""
        if not v and not values.get("DEBUG", False):
            print("⚠️  警告：未设置 DEEPAGENTS_API_KEY，AI 功能将不可用")
        return v


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()

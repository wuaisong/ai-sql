"""
数据库模型定义
使用 SQLAlchemy ORM 定义系统数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, 
    DateTime, Text, JSON, Float, ForeignKey, UniqueConstraint,
    Index, BigInteger, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.pool import QueuePool
import json

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, comment='用户ID')
    username = Column(String(50), unique=True, nullable=False, index=True, comment='用户名')
    email = Column(String(100), unique=True, nullable=True, comment='邮箱')
    hashed_password = Column(String(255), nullable=False, comment='加密密码')
    role = Column(String(20), nullable=False, default='viewer', comment='角色: admin, analyst, viewer')
    is_active = Column(Boolean, default=True, comment='是否激活')
    quota_config = Column(JSON, default=lambda: {}, comment='配额配置')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    queries = relationship('QueryHistory', back_populates='user', cascade='all, delete-orphan')
    usage_records = relationship('UsageRecord', back_populates='user', cascade='all, delete-orphan')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_level': self.event_level,
            'user_id': self.user_id,
            'username': self.username,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 数据库引擎和会话管理
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_engine(self):
        """初始化数据库引擎"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_tables(self):
        """删除所有表（开发环境使用）"""
        Base.metadata.drop_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """获取数据库会话"""
        if not self.SessionLocal:
            self.init_engine()
        return self.SessionLocal()
        
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()


# 默认数据库管理器实例
_db_manager = None


def init_database(database_url: str) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_engine()
    return _db_manager


def get_db() -> Session:
    """获取数据库会话（依赖注入使用）"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager.get_session()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'quota_config': self.quota_config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Datasource(Base):
    """数据源表"""
    __tablename__ = 'datasources'
    
    id = Column(String(36), primary_key=True, comment='数据源ID')
    name = Column(String(100), nullable=False, comment='数据源名称')
    type = Column(String(20), nullable=False, comment='类型: mysql, postgresql, oracle, sqlite')
    host = Column(String(200), nullable=True, comment='主机地址')
    port = Column(Integer, nullable=True, comment='端口')
    database = Column(String(100), nullable=True, comment='数据库名')
    username = Column(String(100), nullable=True, comment='用户名')
    password = Column(String(500), nullable=True, comment='密码（加密存储）')
    file_path = Column(String(500), nullable=True, comment='文件路径（SQLite）')
    connection_string = Column(String(1000), nullable=True, comment='连接字符串')
    
    # 连接配置
    pool_size = Column(Integer, default=5, comment='连接池大小')
    timeout = Column(Integer, default=30, comment='超时时间（秒）')
    max_rows = Column(Integer, default=10000, comment='最大返回行数')
    
    # 状态信息
    status = Column(String(20), default='inactive', comment='状态: active, inactive, error')
    last_connected = Column(DateTime, nullable=True, comment='最后连接时间')
    error_message = Column(Text, nullable=True, comment='错误信息')
    
    # 元数据
    description = Column(Text, nullable=True, comment='描述')
    tags = Column(JSON, default=lambda: [], comment='标签')
    config = Column(JSON, default=lambda: {}, comment='额外配置')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    queries = relationship('QueryHistory', back_populates='datasource', cascade='all, delete-orphan')
    schemas = relationship('SchemaCache', back_populates='datasource', cascade='all, delete-orphan')
    
    # 索引
    __table_args__ = (
        Index('idx_datasource_type', 'type'),
        Index('idx_datasource_status', 'status'),
        Index('idx_datasource_created', 'created_at'),
    )
    
    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'file_path': self.file_path,
            'pool_size': self.pool_size,
            'timeout': self.timeout,
            'max_rows': self.max_rows,
            'status': self.status,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'error_message': self.error_message,
            'description': self.description,
            'tags': self.tags,
            'config': self.config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_password:
            data['password'] = self.password
            
        return data


class QueryHistory(Base):
    """查询历史表"""
    __tablename__ = 'query_history'
    
    id = Column(String(36), primary_key=True, comment='查询ID')
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    datasource_id = Column(String(36), ForeignKey('datasources.id', ondelete='CASCADE'), nullable=False, comment='数据源ID')
    
    # 查询信息
    natural_query = Column(Text, nullable=False, comment='自然语言查询')
    generated_sql = Column(Text, nullable=False, comment='生成的SQL')
    executed_sql = Column(Text, nullable=True, comment='实际执行的SQL')
    query_type = Column(String(20), default='natural', comment='查询类型: natural, sql')
    
    # 执行结果
    success = Column(Boolean, default=True, comment='是否成功')
    error_message = Column(Text, nullable=True, comment='错误信息')
    row_count = Column(Integer, default=0, comment='返回行数')
    execution_time_ms = Column(Float, default=0, comment='执行时间（毫秒）')
    
    # 结果信息
    result_columns = Column(JSON, default=lambda: [], comment='结果列名')
    result_preview = Column(JSON, default=lambda: [], comment='结果预览（前几行）')
    result_size_bytes = Column(BigInteger, default=0, comment='结果大小（字节）')
    
    # 缓存信息
    cache_hit = Column(Boolean, default=False, comment='是否缓存命中')
    cache_key = Column(String(100), nullable=True, comment='缓存键')
    
    # 审计信息
    ip_address = Column(String(45), nullable=True, comment='IP地址')
    user_agent = Column(Text, nullable=True, comment='用户代理')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 关系
    user = relationship('User', back_populates='queries')
    datasource = relationship('Datasource', back_populates='queries')
    
    # 索引
    __table_args__ = (
        Index('idx_query_user', 'user_id'),
        Index('idx_query_datasource', 'datasource_id'),
        Index('idx_query_created', 'created_at'),
        Index('idx_query_success', 'success'),
        Index('idx_query_cache', 'cache_hit'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_level': self.event_level,
            'user_id': self.user_id,
            'username': self.username,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 数据库引擎和会话管理
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_engine(self):
        """初始化数据库引擎"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_tables(self):
        """删除所有表（开发环境使用）"""
        Base.metadata.drop_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """获取数据库会话"""
        if not self.SessionLocal:
            self.init_engine()
        return self.SessionLocal()
        
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()


# 默认数据库管理器实例
_db_manager = None


def init_database(database_url: str) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_engine()
    return _db_manager


def get_db() -> Session:
    """获取数据库会话（依赖注入使用）"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager.get_session()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'datasource_id': self.datasource_id,
            'datasource_name': self.datasource.name if self.datasource else None,
            'datasource_type': self.datasource.type if self.datasource else None,
            'natural_query': self.natural_query,
            'generated_sql': self.generated_sql,
            'executed_sql': self.executed_sql,
            'query_type': self.query_type,
            'success': self.success,
            'error_message': self.error_message,
            'row_count': self.row_count,
            'execution_time_ms': self.execution_time_ms,
            'result_columns': self.result_columns,
            'result_preview': self.result_preview,
            'result_size_bytes': self.result_size_bytes,
            'cache_hit': self.cache_hit,
            'cache_key': self.cache_key,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SchemaCache(Base):
    """Schema缓存表"""
    __tablename__ = 'schema_cache'
    
    id = Column(String(36), primary_key=True, comment='缓存ID')
    datasource_id = Column(String(36), ForeignKey('datasources.id', ondelete='CASCADE'), nullable=False, comment='数据源ID')
    
    # Schema数据
    schema_data = Column(JSON, nullable=False, comment='Schema数据')
    table_count = Column(Integer, default=0, comment='表数量')
    column_count = Column(Integer, default=0, comment='列数量')
    
    # 统计信息
    large_tables = Column(JSON, default=lambda: [], comment='大表列表')
    estimated_total_rows = Column(BigInteger, default=0, comment='预估总行数')
    
    # 缓存信息
    version = Column(String(50), nullable=False, comment='Schema版本')
    checksum = Column(String(64), nullable=False, comment='数据校验和')
    is_valid = Column(Boolean, default=True, comment='是否有效')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    expires_at = Column(DateTime, nullable=True, comment='过期时间')
    
    # 关系
    datasource = relationship('Datasource', back_populates='schemas')
    
    # 索引
    __table_args__ = (
        Index('idx_schema_datasource', 'datasource_id'),
        Index('idx_schema_version', 'version'),
        Index('idx_schema_expires', 'expires_at'),
        UniqueConstraint('datasource_id', 'version', name='uq_datasource_version'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_level': self.event_level,
            'user_id': self.user_id,
            'username': self.username,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 数据库引擎和会话管理
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_engine(self):
        """初始化数据库引擎"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_tables(self):
        """删除所有表（开发环境使用）"""
        Base.metadata.drop_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """获取数据库会话"""
        if not self.SessionLocal:
            self.init_engine()
        return self.SessionLocal()
        
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()


# 默认数据库管理器实例
_db_manager = None


def init_database(database_url: str) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_engine()
    return _db_manager


def get_db() -> Session:
    """获取数据库会话（依赖注入使用）"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager.get_session()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'datasource_id': self.datasource_id,
            'schema_data': self.schema_data,
            'table_count': self.table_count,
            'column_count': self.column_count,
            'large_tables': self.large_tables,
            'estimated_total_rows': self.estimated_total_rows,
            'version': self.version,
            'checksum': self.checksum,
            'is_valid': self.is_valid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class UsageRecord(Base):
    """使用记录表"""
    __tablename__ = 'usage_records'
    
    id = Column(String(36), primary_key=True, comment='记录ID')
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    
    # 时间范围
    period_type = Column(String(10), nullable=False, comment='周期类型: hour, day, month')
    period_start = Column(DateTime, nullable=False, comment='周期开始时间')
    period_end = Column(DateTime, nullable=False, comment='周期结束时间')
    
    # 使用统计
    query_count = Column(Integer, default=0, comment='查询次数')
    total_rows = Column(BigInteger, default=0, comment='总行数')
    total_execution_time_ms = Column(BigInteger, default=0, comment='总执行时间（毫秒）')
    total_result_size_bytes = Column(BigInteger, default=0, comment='总结果大小（字节）')
    
    # 并发统计
    max_concurrent_queries = Column(Integer, default=0, comment='最大并发查询数')
    avg_concurrent_queries = Column(Float, default=0, comment='平均并发查询数')
    
    # 配额使用
    quota_used = Column(JSON, default=lambda: {}, comment='配额使用情况')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系
    user = relationship('User', back_populates='usage_records')
    
    # 索引
    __table_args__ = (
        Index('idx_usage_user', 'user_id'),
        Index('idx_usage_period', 'period_start', 'period_end'),
        Index('idx_usage_type', 'period_type'),
        UniqueConstraint('user_id', 'period_type', 'period_start', name='uq_user_period'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_level': self.event_level,
            'user_id': self.user_id,
            'username': self.username,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 数据库引擎和会话管理
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_engine(self):
        """初始化数据库引擎"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_tables(self):
        """删除所有表（开发环境使用）"""
        Base.metadata.drop_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """获取数据库会话"""
        if not self.SessionLocal:
            self.init_engine()
        return self.SessionLocal()
        
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()


# 默认数据库管理器实例
_db_manager = None


def init_database(database_url: str) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_engine()
    return _db_manager


def get_db() -> Session:
    """获取数据库会话（依赖注入使用）"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager.get_session()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'period_type': self.period_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'query_count': self.query_count,
            'total_rows': self.total_rows,
            'total_execution_time_ms': self.total_execution_time_ms,
            'total_result_size_bytes': self.total_result_size_bytes,
            'max_concurrent_queries': self.max_concurrent_queries,
            'avg_concurrent_queries': self.avg_concurrent_queries,
            'quota_used': self.quota_used,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = 'system_configs'
    
    id = Column(String(36), primary_key=True, comment='配置ID')
    key = Column(String(100), unique=True, nullable=False, index=True, comment='配置键')
    value = Column(JSON, nullable=False, comment='配置值')
    description = Column(Text, nullable=True, comment='描述')
    is_encrypted = Column(Boolean, default=False, comment='是否加密')
    is_system = Column(Boolean, default=False, comment='是否系统配置')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_level': self.event_level,
            'user_id': self.user_id,
            'username': self.username,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 数据库引擎和会话管理
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_engine(self):
        """初始化数据库引擎"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_tables(self):
        """删除所有表（开发环境使用）"""
        Base.metadata.drop_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """获取数据库会话"""
        if not self.SessionLocal:
            self.init_engine()
        return self.SessionLocal()
        
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()


# 默认数据库管理器实例
_db_manager = None


def init_database(database_url: str) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_engine()
    return _db_manager


def get_db() -> Session:
    """获取数据库会话（依赖注入使用）"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager.get_session()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'is_encrypted': self.is_encrypted,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = 'audit_logs'
    
    id = Column(String(36), primary_key=True, comment='日志ID')
    
    # 事件信息
    event_type = Column(String(50), nullable=False, comment='事件类型')
    event_level = Column(String(20), default='INFO', comment='事件级别: INFO, WARNING, ERROR')
    
    # 用户信息
    user_id = Column(String(36), nullable=True, comment='用户ID')
    username = Column(String(100), nullable=True, comment='用户名')
    
    # 资源信息
    resource_type = Column(String(50), nullable=True, comment='资源类型')
    resource_id = Column(String(100), nullable=True, comment='资源ID')
    
    # 操作信息
    action = Column(String(100), nullable=True, comment='操作')
    details = Column(JSON, default=lambda: {}, comment='详细信息')
    
    # 网络信息
    ip_address = Column(String(45), nullable=True, comment='IP地址')
    user_agent = Column(Text, nullable=True, comment='用户代理')
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 索引
    __table_args__ = (
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_level', 'event_level'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_level': self.event_level,
            'user_id': self.user_id,
            'username': self.username,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 数据库引擎和会话管理
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_engine(self):
        """初始化数据库引擎"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_tables(self):
        """删除所有表（开发环境使用）"""
        Base.metadata.drop_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """获取数据库会话"""
        if not self.SessionLocal:
            self.init_engine()
        return self.SessionLocal()
        
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()


# 默认数据库管理器实例
_db_manager = None


def init_database(database_url: str) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_engine()
    return _db_manager


def get_db() -> Session:
    """获取数据库会话（依赖注入使用）"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager.get_session()


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    if not _db_manager:
        raise RuntimeError("数据库未初始化，请先调用 init_database")
    return _db_manager
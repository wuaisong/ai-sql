"""
连接池管理服务
统一管理所有数据源连接，支持连接复用和监控
"""
import threading
import time
from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from connectors import MySQLConnector, PostgreSQLConnector, OracleConnector
from models.database import Datasource, get_db
from config.settings import settings

logger = logging.getLogger(__name__)


class ConnectionStatus(str, Enum):
    """连接状态"""
    IDLE = "idle"          # 空闲
    BUSY = "busy"          # 使用中
    ERROR = "error"        # 错误
    CLOSED = "closed"      # 已关闭


@dataclass
class ConnectionStats:
    """连接统计"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    error_connections: int = 0
    total_queries: int = 0
    total_query_time_ms: float = 0
    avg_query_time_ms: float = 0
    last_activity: Optional[datetime] = None


@dataclass
class PooledConnection:
    """池化连接"""
    datasource_id: str
    connector: Any
    status: ConnectionStatus = ConnectionStatus.IDLE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    use_count: int = 0
    total_use_time_ms: float = 0
    error_count: int = 0
    last_error: Optional[str] = None
    
    @property
    def avg_use_time_ms(self) -> float:
        """平均使用时间"""
        return self.total_use_time_ms / self.use_count if self.use_count > 0 else 0
    
    @property
    def is_healthy(self) -> bool:
        """连接是否健康"""
        if self.status == ConnectionStatus.ERROR:
            return False
        if self.error_count > 10:  # 错误次数过多
            return False
        if self.created_at < datetime.utcnow() - timedelta(hours=24):  # 连接太旧
            return False
        return True


class ConnectionPool:
    """连接池"""
    
    def __init__(self, max_pool_size: int = 10, idle_timeout: int = 300):
        self.max_pool_size = max_pool_size
        self.idle_timeout = idle_timeout  # 空闲超时时间（秒）
        self._pools: Dict[str, List[PooledConnection]] = {}
        self._lock = threading.RLock()
        self._stats = ConnectionStats()
        self._cleanup_thread = None
        self._running = False
        
    def start(self):
        """启动连接池"""
        if not self._running:
            self._running = True
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="ConnectionPoolCleanup"
            )
            self._cleanup_thread.start()
            logger.info("连接池已启动")
    
    def stop(self):
        """停止连接池"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        self.close_all()
        logger.info("连接池已停止")
    
    def get_connection(self, datasource_id: str, datasource_config: Dict[str, Any]) -> PooledConnection:
        """
        获取连接
        
        Args:
            datasource_id: 数据源ID
            datasource_config: 数据源配置
            
        Returns:
            池化连接
        """
        with self._lock:
            # 检查是否已有连接池
            if datasource_id not in self._pools:
                self._pools[datasource_id] = []
            
            pool = self._pools[datasource_id]
            
            # 1. 尝试获取空闲连接
            for conn in pool:
                if conn.status == ConnectionStatus.IDLE and conn.is_healthy:
                    conn.status = ConnectionStatus.BUSY
                    conn.last_used = datetime.utcnow()
                    conn.use_count += 1
                    self._stats.active_connections += 1
                    self._stats.idle_connections -= 1
                    self._stats.last_activity = datetime.utcnow()
                    return conn
            
            # 2. 检查是否达到最大连接数
            if len(pool) >= self.max_pool_size:
                # 尝试清理不健康的连接
                self._cleanup_pool(datasource_id)
                
                if len(pool) >= self.max_pool_size:
                    raise ConnectionError(f"连接池已满，最大连接数: {self.max_pool_size}")
            
            # 3. 创建新连接
            logger.info(f"创建新连接: {datasource_id}")
            connector = self._create_connector(datasource_config)
            
            try:
                if not connector.connect():
                    raise ConnectionError(f"连接失败: {datasource_id}")
                
                conn = PooledConnection(
                    datasource_id=datasource_id,
                    connector=connector,
                    status=ConnectionStatus.BUSY,
                    last_used=datetime.utcnow(),
                    use_count=1
                )
                
                pool.append(conn)
                self._stats.total_connections += 1
                self._stats.active_connections += 1
                self._stats.last_activity = datetime.utcnow()
                
                return conn
                
            except Exception as e:
                logger.error(f"创建连接失败: {datasource_id}, 错误: {e}")
                raise
    
    def release_connection(self, conn: PooledConnection, execution_time_ms: float = 0):
        """
        释放连接
        
        Args:
            conn: 池化连接
            execution_time_ms: 执行时间（毫秒）
        """
        with self._lock:
            if conn.status == ConnectionStatus.CLOSED:
                return
            
            conn.status = ConnectionStatus.IDLE
            conn.last_used = datetime.utcnow()
            conn.total_use_time_ms += execution_time_ms
            
            self._stats.active_connections -= 1
            self._stats.idle_connections += 1
            self._stats.total_queries += 1
            self._stats.total_query_time_ms += execution_time_ms
            self._stats.avg_query_time_ms = (
                self._stats.total_query_time_ms / self._stats.total_queries
                if self._stats.total_queries > 0 else 0
            )
    
    def mark_error(self, conn: PooledConnection, error: str):
        """标记连接错误"""
        with self._lock:
            conn.status = ConnectionStatus.ERROR
            conn.error_count += 1
            conn.last_error = str(error)
            
            self._stats.active_connections -= 1
            self._stats.error_connections += 1
    
    def close_connection(self, conn: PooledConnection):
        """关闭连接"""
        with self._lock:
            try:
                conn.connector.disconnect()
            except:
                pass
            
            conn.status = ConnectionStatus.CLOSED
            
            # 从池中移除
            if conn.datasource_id in self._pools:
                pool = self._pools[conn.datasource_id]
                if conn in pool:
                    pool.remove(conn)
            
            self._stats.total_connections -= 1
            if conn.status == ConnectionStatus.ERROR:
                self._stats.error_connections -= 1
            elif conn.status == ConnectionStatus.IDLE:
                self._stats.idle_connections -= 1
            elif conn.status == ConnectionStatus.BUSY:
                self._stats.active_connections -= 1
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for datasource_id, pool in list(self._pools.items()):
                for conn in list(pool):
                    self.close_connection(conn)
            
            self._pools.clear()
            logger.info("所有连接已关闭")
    
    def get_stats(self) -> ConnectionStats:
        """获取统计信息"""
        with self._lock:
            return ConnectionStats(
                total_connections=self._stats.total_connections,
                active_connections=self._stats.active_connections,
                idle_connections=self._stats.idle_connections,
                error_connections=self._stats.error_connections,
                total_queries=self._stats.total_queries,
                total_query_time_ms=self._stats.total_query_time_ms,
                avg_query_time_ms=self._stats.avg_query_time_ms,
                last_activity=self._stats.last_activity
            )
    
    def get_pool_stats(self, datasource_id: str) -> Dict[str, Any]:
        """获取指定数据源的连接池统计"""
        with self._lock:
            if datasource_id not in self._pools:
                return {}
            
            pool = self._pools[datasource_id]
            stats = {
                'total': len(pool),
                'idle': sum(1 for c in pool if c.status == ConnectionStatus.IDLE),
                'busy': sum(1 for c in pool if c.status == ConnectionStatus.BUSY),
                'error': sum(1 for c in pool if c.status == ConnectionStatus.ERROR),
                'avg_use_time_ms': sum(c.avg_use_time_ms for c in pool) / len(pool) if pool else 0,
                'oldest_connection': min(c.created_at for c in pool).isoformat() if pool else None,
                'newest_connection': max(c.created_at for c in pool).isoformat() if pool else None
            }
            
            return stats
    
    def _create_connector(self, config: Dict[str, Any]) -> Any:
        """创建连接器"""
        ds_type = config.get('type', 'mysql').lower()
        
        common_params = {
            'host': config.get('host'),
            'port': config.get('port'),
            'database': config.get('database'),
            'username': config.get('username'),
            'password': config.get('password'),
            'pool_size': config.get('pool_size', 5),
            'timeout': config.get('timeout', 30)
        }
        
        if ds_type == 'mysql':
            return MySQLConnector(**common_params)
        elif ds_type == 'postgresql':
            return PostgreSQLConnector(**common_params)
        elif ds_type == 'oracle':
            return OracleConnector(**common_params)
        else:
            raise ValueError(f"不支持的数据源类型: {ds_type}")
    
    def _cleanup_pool(self, datasource_id: str):
        """清理连接池"""
        if datasource_id not in self._pools:
            return
        
        pool = self._pools[datasource_id]
        to_remove = []
        
        for conn in pool:
            # 清理不健康的连接
            if not conn.is_healthy:
                to_remove.append(conn)
            # 清理空闲时间过长的连接
            elif (conn.status == ConnectionStatus.IDLE and 
                  conn.last_used and 
                  datetime.utcnow() - conn.last_used > timedelta(seconds=self.idle_timeout)):
                to_remove.append(conn)
        
        for conn in to_remove:
            self.close_connection(conn)
    
    def _cleanup_loop(self):
        """清理循环"""
        while self._running:
            try:
                time.sleep(60)  # 每分钟清理一次
                
                with self._lock:
                    for datasource_id in list(self._pools.keys()):
                        self._cleanup_pool(datasource_id)
                        
            except Exception as e:
                logger.error(f"连接池清理失败: {e}")
    
    @contextmanager
    def get_managed_connection(self, datasource_id: str, datasource_config: Dict[str, Any]):
        """
        获取托管连接（上下文管理器）
        
        Args:
            datasource_id: 数据源ID
            datasource_config: 数据源配置
            
        Yields:
            连接器实例
        """
        conn = None
        start_time = time.time()
        
        try:
            conn = self.get_connection(datasource_id, datasource_config)
            yield conn.connector
            
        except Exception as e:
            if conn:
                self.mark_error(conn, str(e))
            raise
            
        finally:
            if conn:
                execution_time_ms = (time.time() - start_time) * 1000
                self.release_connection(conn, execution_time_ms)


class ConnectionPoolManager:
    """连接池管理器（单例）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._pool = ConnectionPool(
            max_pool_size=settings.get('CONNECTION_POOL_MAX_SIZE', 20),
            idle_timeout=settings.get('CONNECTION_POOL_IDLE_TIMEOUT', 300)
        )
        self._pool.start()
        self._initialized = True
    
    def get_connection(self, datasource_id: str) -> Any:
        """
        获取连接
        
        Args:
            datasource_id: 数据源ID
            
        Returns:
            连接器实例
        """
        # 从数据库获取数据源配置
        db = get_db()
        try:
            datasource = db.query(Datasource).filter_by(id=datasource_id).first()
            if not datasource:
                raise ValueError(f"数据源不存在: {datasource_id}")
            
            config = datasource.to_dict(include_password=True)
            return self._pool.get_connection(datasource_id, config).connector
            
        finally:
            db.close()
    
    @contextmanager
    def managed_connection(self, datasource_id: str):
        """
        获取托管连接
        
        Args:
            datasource_id: 数据源ID
            
        Yields:
            连接器实例
        """
        db = get_db()
        try:
            datasource = db.query(Datasource).filter_by(id=datasource_id).first()
            if not datasource:
                raise ValueError(f"数据源不存在: {datasource_id}")
            
            config = datasource.to_dict(include_password=True)
            
            with self._pool.get_managed_connection(datasource_id, config) as connector:
                yield connector
                
        finally:
            db.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._pool.get_stats()
        return {
            'total_connections': stats.total_connections,
            'active_connections': stats.active_connections,
            'idle_connections': stats.idle_connections,
            'error_connections': stats.error_connections,
            'total_queries': stats.total_queries,
            'avg_query_time_ms': stats.avg_query_time_ms,
            'pools': {
                ds_id: self._pool.get_pool_stats(ds_id)
                for ds_id in self._pool._pools.keys()
            }
        }
    
    def close_all(self):
        """关闭所有连接"""
        self._pool.close_all()
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, '_pool'):
            self._pool.stop()


# 全局连接池管理器实例
connection_pool_manager = ConnectionPoolManager()
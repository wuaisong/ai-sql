"""
数据源连接器基类
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd


class BaseConnector(ABC):
    """数据源连接器基类"""
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        **kwargs
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.extra_params = kwargs
        self.connection = None
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def execute_query(self, sql: str, params: Optional[Dict] = None, 
                     limit: int = 10000, timeout: int = 60) -> Tuple[List[Dict], List[str]]:
        """
        执行查询
        
        Args:
            sql: SQL 语句
            params: 参数
            limit: 结果行数限制
            timeout: 超时时间（秒）
            
        Returns:
            (数据列表，列名列表)
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """获取数据库 schema 信息"""
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        pass
    
    @abstractmethod
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        pass
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self._connected:
                self.connect()
            
            # 执行简单查询测试
            result = self.execute_query("SELECT 1")
            return result[0] is not None
        except Exception as e:
            print(f"连接测试失败：{e}")
            return False
    
    def execute_with_cache(
        self, 
        sql: str, 
        cache_key: Optional[str] = None,
        cache_ttl: int = 300
    ) -> Tuple[List[Dict], List[str], bool]:
        """
        带缓存的查询执行
        
        Args:
            sql: SQL 语句
            cache_key: 缓存键
            cache_ttl: 缓存 TTL（秒）
            
        Returns:
            (数据，列名，是否来自缓存)
        """
        # 子类可以实现缓存逻辑
        return self.execute_query(sql), False
    
    def get_table_description(self, table_name: str) -> Optional[str]:
        """获取表描述（如果支持）"""
        return None
    
    def get_column_description(self, table_name: str, column_name: str) -> Optional[str]:
        """获取列描述（如果支持）"""
        return None
    
    @property
    def connected(self) -> bool:
        """连接状态"""
        return self._connected
    
    @property
    def connection_info(self) -> Dict[str, Any]:
        """连接信息（不含密码）"""
        return {
            "type": self.__class__.__name__,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "connected": self._connected
        }

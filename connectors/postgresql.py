"""
PostgreSQL 数据源连接器
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseConnector


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL 连接器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "",
        username: str = "postgres",
        password: str = "",
        schema: str = "public",
        pool_size: int = 5,
        **kwargs
    ):
        super().__init__(host, port, database, username, password, **kwargs)
        self.schema = schema
        self.pool_size = pool_size
        self.engine = None
        self.inspector = None
    
    def connect(self) -> bool:
        """建立 PostgreSQL 连接"""
        try:
            connection_url = (
                f"postgresql+psycopg2://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
            
            self.engine = create_engine(
                connection_url,
                pool_size=self.pool_size,
                max_overflow=10,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.inspector = inspect(self.engine)
            self._connected = True
            return True
            
        except SQLAlchemyError as e:
            raise ConnectionError(f"PostgreSQL 连接失败：{str(e)}")
    
    def disconnect(self):
        """断开连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.inspector = None
            self._connected = False
    
    def execute_query(
        self, 
        sql: str, 
        params: Optional[Dict] = None,
        limit: int = 10000, 
        timeout: int = 60
    ) -> Tuple[List[Dict], List[str]]:
        """执行 SQL 查询"""
        if not self._connected:
            self.connect()
        
        try:
            sql_upper = sql.strip().upper()
            if "LIMIT" not in sql_upper and sql_upper.startswith("SELECT"):
                sql = f"{sql.rstrip(';')} LIMIT {limit}"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                columns = list(result.keys())
                data = [dict(zip(columns, row)) for row in result.fetchall()]
                
                return data, columns
                
        except SQLAlchemyError as e:
            raise QueryError(f"SQL 执行失败：{str(e)}")
    
    def get_schema(self) -> Dict[str, Any]:
        """获取数据库 schema 信息"""
        if not self._connected:
            self.connect()
        
        tables = {}
        
        for table_name in self.get_tables():
            columns = []
            for col in self.get_table_columns(table_name):
                columns.append({
                    "name": col["name"],
                    "type": col["type"],
                    "nullable": col.get("nullable", True),
                    "description": col.get("comment", "")
                })
            
            tables[table_name] = {
                "columns": columns,
                "description": self.get_table_description(table_name) or "",
                "relationships": []
            }
        
        return {"tables": tables, "database": self.database, "schema": self.schema}
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        if not self._connected:
            self.connect()
        
        return self.inspector.get_table_names(schema=self.schema)
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        if not self._connected:
            self.connect()
        
        columns = []
        for col in self.inspector.get_columns(table_name, schema=self.schema):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "comment": col.get("comment", "")
            })
        
        return columns
    
    def get_table_description(self, table_name: str) -> Optional[str]:
        """获取表注释"""
        if not self._connected:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT obj_description(c.oid, 'pg_class') as comment
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = '{table_name}'
                    AND n.nspname = '{self.schema}'
                """))
                row = result.fetchone()
                return row[0] if row and row[0] else None
        except:
            return None


class QueryError(Exception):
    """查询错误"""
    pass

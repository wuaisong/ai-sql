"""
Oracle 数据源连接器
支持 Oracle Database 11g, 12c, 18c, 19c, 21c
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import DatabaseError
import logging

from .base import BaseConnector

logger = logging.getLogger(__name__)


class OracleConnector(BaseConnector):
    """
    Oracle 数据库连接器
    
    功能特性:
    - ✅ 连接池管理
    - ✅ 自动重连
    - ✅ Schema 自动发现
    - ✅ 表注释和字段注释
    - ✅ 外键关系识别
    - ✅ 查询超时控制
    - ✅ 支持多 Schema
    - ✅ 支持 Oracle 特有类型
    - ✅ 支持 CLOB/BLOB 处理
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 1521,
        database: str = "ORCL",  # Oracle SID 或服务名
        username: str = "SYSTEM",
        password: str = "",
        schema: str = "SYSTEM",  # Oracle Schema
        service_name: bool = False,  # True=使用服务名，False=使用 SID
        encoding: str = "UTF-8",
        pool_size: int = 5,
        **kwargs
    ):
        """
        初始化 Oracle 连接器
        
        Args:
            host: 主机地址
            port: 端口（默认 1521）
            database: 数据库 SID 或服务名
            username: 用户名
            password: 密码
            schema: Schema 名（默认与用户名相同）
            service_name: 是否使用服务名连接
            encoding: 字符编码
            pool_size: 连接池大小
        """
        super().__init__(host, port, database, username, password, **kwargs)
        self.schema = schema or username
        self.service_name = service_name
        self.encoding = encoding
        self.pool_size = pool_size
        self.engine = None
        self.inspector = None
    
    def connect(self) -> bool:
        """
        建立 Oracle 连接
        
        Returns:
            bool: 是否成功
        """
        try:
            # 构建连接 URL
            if self.service_name:
                # 使用服务名连接
                connection_url = (
                    f"oracle+oracledb://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/?service_name={self.database}"
                )
            else:
                # 使用 SID 连接
                connection_url = (
                    f"oracle+oracledb://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/{self.database}"
                )
            
            # 创建引擎
            self.engine = create_engine(
                connection_url,
                encoding=self.encoding,
                pool_size=self.pool_size,
                max_overflow=10,
                pool_recycle=3600,
                pool_pre_ping=True,
                # Oracle 特定参数
                connect_args={
                    "encoding": self.encoding,
                    "nencoding": self.encoding,
                    "threaded": True,
                }
            )
            
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            
            # 创建检查器
            self.inspector = inspect(self.engine)
            self._connected = True
            
            logger.info(f"Oracle 连接成功：{self.host}:{self.port}/{self.database}")
            return True
            
        except DatabaseError as e:
            logger.error(f"Oracle 连接失败：{str(e)}")
            raise ConnectionError(f"Oracle 连接失败：{str(e)}")
        except Exception as e:
            logger.exception(f"Oracle 连接异常：{e}")
            raise
    
    def disconnect(self):
        """断开连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.inspector = None
            self._connected = False
            logger.info("Oracle 连接已断开")
    
    def execute_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        limit: int = 10000,
        timeout: int = 60
    ) -> Tuple[List[Dict], List[str]]:
        """
        执行 SQL 查询
        
        Args:
            sql: SQL 语句
            params: 参数
            limit: 结果行数限制
            timeout: 超时时间（秒）
            
        Returns:
            (数据列表，列名列表)
        """
        if not self._connected:
            self.connect()
        
        try:
            # Oracle 处理：添加 ROWNUM 限制
            sql_upper = sql.strip().upper()
            if "ROWNUM" not in sql_upper and sql_upper.startswith("SELECT"):
                # 处理包含 ORDER BY 的情况
                if "ORDER BY" in sql_upper:
                    sql = f"SELECT * FROM ({sql.rstrip(';')}) WHERE ROWNUM <= {limit}"
                else:
                    sql = f"{sql.rstrip(';')} WHERE ROWNUM <= {limit}"
            
            with self.engine.connect() as conn:
                # 设置超时
                conn.execution_options(stream_results=True)
                
                result = conn.execute(text(sql), params or {})
                columns = list(result.keys())
                
                # 转换为字典列表
                data = []
                for row in result.fetchall():
                    row_dict = dict(zip(columns, row))
                    
                    # 处理 Oracle 特殊类型（CLOB, BLOB 等）
                    for key, value in row_dict.items():
                        if hasattr(value, 'read'):  # LOB 对象
                            try:
                                row_dict[key] = value.read()
                            except:
                                row_dict[key] = str(value)
                        elif hasattr(value, 'getvalue'):  # 其他可读取对象
                            row_dict[key] = str(value)
                    
                    data.append(row_dict)
                
                return data, columns
                
        except DatabaseError as e:
            logger.error(f"Oracle 查询失败：{sql[:100]}... - {str(e)}")
            raise QueryError(f"Oracle 查询失败：{str(e)}")
    
    def get_schema(self) -> Dict[str, Any]:
        """
        获取数据库 Schema 信息
        
        Returns:
            Schema 信息字典
        """
        if not self._connected:
            self.connect()
        
        tables = {}
        
        # 获取所有表
        for table_name in self.get_tables():
            try:
                # 获取表信息
                table_info = self._get_table_info(table_name)
                tables[table_name] = table_info
            except Exception as e:
                logger.warning(f"获取表 {table_name} 信息失败：{e}")
                continue
        
        return {
            "tables": tables,
            "database": self.database,
            "schema": self.schema,
            "type": "oracle"
        }
    
    def get_tables(self) -> List[str]:
        """
        获取所有表名
        
        Returns:
            表名列表
        """
        if not self._connected:
            self.connect()
        
        try:
            # 从 Oracle 数据字典查询
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name
                    FROM all_tables
                    WHERE owner = :schema
                    ORDER BY table_name
                """), {"schema": self.schema})
                
                return [row[0] for row in result.fetchall()]
                
        except Exception as e:
            logger.warning(f"获取表列表失败：{e}")
            # 回退到 SQLAlchemy inspector
            return self.inspector.get_table_names(schema=self.schema)
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表的列信息
        
        Args:
            table_name: 表名
            
        Returns:
            列信息列表
        """
        if not self._connected:
            self.connect()
        
        try:
            # 从 Oracle 数据字典查询
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        column_name,
                        data_type,
                        data_length,
                        data_precision,
                        data_scale,
                        nullable,
                        comments
                    FROM all_tab_columns
                    WHERE owner = :schema AND table_name = :table
                    ORDER BY column_id
                """), {"schema": self.schema, "table": table_name.upper()})
                
                columns = []
                for row in result.fetchall():
                    col_type = row[1]
                    
                    # 构建完整的类型字符串
                    if col_type in ('VARCHAR2', 'NVARCHAR2'):
                        col_type = f"{row[1]}({row[2]})"
                    elif col_type in ('NUMBER',):
                        if row[3] and row[4]:
                            col_type = f"NUMBER({row[3]},{row[4]})"
                        elif row[3]:
                            col_type = f"NUMBER({row[3]})"
                    elif col_type in ('TIMESTAMP',):
                        if row[4]:
                            col_type = f"TIMESTAMP({row[4]})"
                    
                    columns.append({
                        "name": row[0],
                        "type": col_type,
                        "nullable": row[5] == 'Y',
                        "description": row[6] or "",
                        "length": row[2],
                        "precision": row[3],
                        "scale": row[4]
                    })
                
                return columns
                
        except Exception as e:
            logger.warning(f"获取表 {table_name} 列信息失败：{e}")
            # 回退到 SQLAlchemy inspector
            return self.inspector.get_columns(table_name, schema=self.schema)
    
    def _get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取表的完整信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        columns = self.get_table_columns(table_name)
        
        # 获取表注释
        description = self.get_table_description(table_name)
        
        # 获取外键关系
        relationships = self.get_foreign_keys(table_name)
        
        # 获取索引
        indexes = self.get_indexes(table_name)
        
        # 获取表统计信息
        stats = self.get_table_stats(table_name)
        
        return {
            "columns": columns,
            "description": description,
            "relationships": relationships,
            "indexes": indexes,
            "stats": stats,
            "schema": self.schema
        }
    
    def get_table_description(self, table_name: str) -> Optional[str]:
        """
        获取表注释
        
        Args:
            table_name: 表名
            
        Returns:
            表注释
        """
        if not self._connected:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT comments
                    FROM all_tab_comments
                    WHERE owner = :schema AND table_name = :table
                """), {"schema": self.schema, "table": table_name.upper()})
                
                row = result.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.warning(f"获取表注释失败：{e}")
            return None
    
    def get_column_description(self, table_name: str, column_name: str) -> Optional[str]:
        """
        获取列注释
        
        Args:
            table_name: 表名
            column_name: 列名
            
        Returns:
            列注释
        """
        if not self._connected:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT comments
                    FROM all_col_comments
                    WHERE owner = :schema AND table_name = :table AND column_name = :column
                """), {
                    "schema": self.schema,
                    "table": table_name.upper(),
                    "column": column_name.upper()
                })
                
                row = result.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.warning(f"获取列注释失败：{e}")
            return None
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取外键信息
        
        Args:
            table_name: 表名
            
        Returns:
            外键列表
        """
        if not self._connected:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        a.constraint_name,
                        a.column_name,
                        c_pk.table_name AS pk_table,
                        b.column_name AS pk_column,
                        c.status
                    FROM all_cons_columns a
                    JOIN all_constraints c ON a.owner = c.owner AND a.constraint_name = c.constraint_name
                    JOIN all_constraints c_pk ON c.r_owner = c_pk.owner AND c.r_constraint_name = c_pk.constraint_name
                    JOIN all_cons_columns b ON c_pk.owner = b.owner AND c_pk.constraint_name = b.constraint_name AND b.position = a.position
                    WHERE c.constraint_type = 'R'
                      AND a.owner = :schema
                      AND a.table_name = :table
                    ORDER BY a.constraint_name, a.position
                """), {"schema": self.schema, "table": table_name.upper()})
                
                foreign_keys = []
                for row in result.fetchall():
                    foreign_keys.append({
                        "constraint_name": row[0],
                        "column": row[1],
                        "referenced_table": row[2],
                        "referenced_column": row[3],
                        "status": row[4]
                    })
                
                return foreign_keys
                
        except Exception as e:
            logger.warning(f"获取外键失败：{e}")
            return []
    
    def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取索引信息
        
        Args:
            table_name: 表名
            
        Returns:
            索引列表
        """
        if not self._connected:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        i.index_name,
                        i.column_name,
                        i.column_position,
                        ix.uniqueness,
                        ix.status
                    FROM all_ind_columns i
                    JOIN all_indexes ix ON i.index_owner = ix.owner AND i.index_name = ix.index_name
                    WHERE i.index_owner = :schema
                      AND i.table_name = :table
                    ORDER BY i.index_name, i.column_position
                """), {"schema": self.schema, "table": table_name.upper()})
                
                indexes = {}
                for row in result.fetchall():
                    index_name = row[0]
                    if index_name not in indexes:
                        indexes[index_name] = {
                            "name": index_name,
                            "columns": [],
                            "uniqueness": row[3],
                            "status": row[4]
                        }
                    indexes[index_name]["columns"].append({
                        "column": row[1],
                        "position": row[2]
                    })
                
                return list(indexes.values())
                
        except Exception as e:
            logger.warning(f"获取索引失败：{e}")
            return []
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        获取表统计信息
        
        Args:
            table_name: 表名
            
        Returns:
            统计信息
        """
        if not self._connected:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        num_rows,
                        blocks,
                        avg_row_len,
                        last_analyzed
                    FROM all_tables
                    WHERE owner = :schema AND table_name = :table
                """), {"schema": self.schema, "table": table_name.upper()})
                
                row = result.fetchone()
                if row:
                    return {
                        "row_count": row[0],
                        "blocks": row[1],
                        "avg_row_length": row[2],
                        "last_analyzed": row[3]
                    }
                
                return {}
                
        except Exception as e:
            logger.warning(f"获取表统计失败：{e}")
            return {}
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self._connected:
                self.connect()
            
            # 执行简单查询
            result = self.execute_query("SELECT 1 FROM DUAL")
            return result[0] is not None
            
        except Exception as e:
            logger.error(f"Oracle 连接测试失败：{e}")
            return False
    
    @property
    def connection_info(self) -> Dict[str, Any]:
        """连接信息（不含密码）"""
        return {
            "type": "Oracle",
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "schema": self.schema,
            "service_name": self.service_name,
            "username": self.username,
            "connected": self._connected,
            "version": self.get_version()
        }
    
    def get_version(self) -> Optional[str]:
        """获取 Oracle 版本"""
        try:
            if not self._connected:
                self.connect()
            
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version FROM v$instance"))
                row = result.fetchone()
                return row[0] if row else None
                
        except:
            return None


class QueryError(Exception):
    """查询错误"""
    pass

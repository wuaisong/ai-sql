"""
数据源管理服务
提供数据源的 CRUD 操作和连接管理
"""
import json
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
import logging

from models.database import Datasource, SchemaCache, get_db
from services.connection_pool import connection_pool_manager
from connectors import MySQLConnector, PostgreSQLConnector, OracleConnector
from config.settings import settings

logger = logging.getLogger(__name__)


class DatasourceService:
    """数据源服务"""
    
    def __init__(self):
        self.encryption_key = settings.SECRET_KEY[:32].encode()  # 简化加密
    
    def encrypt_password(self, password: str) -> str:
        """加密密码（简化实现，生产环境应使用专业加密库）"""
        if not password:
            return ""
        # 使用 SHA256 哈希（生产环境应使用 bcrypt 或 argon2）
        return hashlib.sha256((password + self.encryption_key.decode()).encode()).hexdigest()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码（简化实现，实际应存储哈希而非加密）"""
        # 注意：这里存储的是哈希，无法解密
        # 实际应存储哈希值，验证时比较哈希
        return ""  # 返回空字符串，连接时使用存储的哈希
    
    def get_datasource(self, datasource_id: str, include_password: bool = False) -> Optional[Dict[str, Any]]:
        """获取数据源"""
        db = get_db()
        try:
            datasource = db.query(Datasource).filter_by(id=datasource_id).first()
            if not datasource:
                return None
            
            return datasource.to_dict(include_password=include_password)
            
        except Exception as e:
            logger.error(f"获取数据源失败: {e}")
            return None
        finally:
            db.close()
    
    def list_datasources(
        self, 
        page: int = 1, 
        page_size: int = 20,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """列出数据源"""
        db = get_db()
        try:
            query = db.query(Datasource)
            
            # 应用过滤器
            if type_filter:
                query = query.filter_by(type=type_filter)
            
            if status_filter:
                query = query.filter_by(status=status_filter)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Datasource.name.ilike(search_term)) |
                    (Datasource.host.ilike(search_term)) |
                    (Datasource.description.ilike(search_term))
                )
            
            # 分页
            total = query.count()
            datasources = query.order_by(Datasource.created_at.desc()) \
                             .offset((page - 1) * page_size) \
                             .limit(page_size) \
                             .all()
            
            # 获取连接池统计
            pool_stats = {}
            for ds in datasources:
                stats = connection_pool_manager.get_stats()
                pool_stats[ds.id] = stats['pools'].get(ds.id, {})
            
            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'datasources': [ds.to_dict() for ds in datasources],
                'pool_stats': pool_stats
            }
            
        except Exception as e:
            logger.error(f"列出数据源失败: {e}")
            return {'total': 0, 'datasources': [], 'pool_stats': {}}
        finally:
            db.close()
    
    def create_datasource(self, datasource_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """创建数据源"""
        db = get_db()
        try:
            # 检查数据源ID是否已存在
            existing = db.query(Datasource).filter_by(id=datasource_data['id']).first()
            if existing:
                return False, None, "数据源ID已存在"
            
            # 加密密码
            if 'password' in datasource_data and datasource_data['password']:
                datasource_data['password'] = self.encrypt_password(datasource_data['password'])
            
            # 创建数据源
            datasource = Datasource(**datasource_data)
            datasource.status = 'inactive'  # 初始状态
            
            db.add(datasource)
            db.commit()
            
            # 测试连接
            test_success, test_message = self.test_connection(datasource.id)
            if test_success:
                datasource.status = 'active'
                datasource.last_connected = datetime.utcnow()
            else:
                datasource.status = 'error'
                datasource.error_message = test_message
            
            db.commit()
            
            return True, datasource.to_dict(), test_message
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建数据源失败: {e}")
            return False, None, str(e)
        finally:
            db.close()
    
    def update_datasource(
        self, 
        datasource_id: str, 
        update_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """更新数据源"""
        db = get_db()
        try:
            datasource = db.query(Datasource).filter_by(id=datasource_id).first()
            if not datasource:
                return False, None, "数据源不存在"
            
            # 更新字段
            for key, value in update_data.items():
                if key == 'password' and value:
                    # 加密新密码
                    setattr(datasource, key, self.encrypt_password(value))
                elif hasattr(datasource, key):
                    setattr(datasource, key, value)
            
            # 测试连接
            test_success, test_message = self.test_connection(datasource_id)
            if test_success:
                datasource.status = 'active'
                datasource.last_connected = datetime.utcnow()
                datasource.error_message = None
            else:
                datasource.status = 'error'
                datasource.error_message = test_message
            
            db.commit()
            
            # 使连接池中的旧连接失效
            connection_pool_manager.close_all()
            
            return True, datasource.to_dict(), test_message
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新数据源失败: {e}")
            return False, None, str(e)
        finally:
            db.close()
    
    def delete_datasource(self, datasource_id: str) -> Tuple[bool, str]:
        """删除数据源"""
        db = get_db()
        try:
            datasource = db.query(Datasource).filter_by(id=datasource_id).first()
            if not datasource:
                return False, "数据源不存在"
            
            # 删除相关缓存
            self.clear_schema_cache(datasource_id)
            
            # 从连接池移除
            connection_pool_manager.close_all()
            
            # 删除数据源
            db.delete(datasource)
            db.commit()
            
            return True, "删除成功"
            
        except Exception as e:
            db.rollback()
            logger.error(f"删除数据源失败: {e}")
            return False, str(e)
        finally:
            db.close()
    
    def test_connection(self, datasource_id: str) -> Tuple[bool, str]:
        """测试连接"""
        try:
            with connection_pool_manager.managed_connection(datasource_id) as connector:
                success = connector.test_connection()
                return success, "连接成功" if success else "连接失败"
                
        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            return False, str(e)
    
    def get_schema(self, datasource_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """获取数据源 Schema"""
        db = get_db()
        try:
            # 检查缓存
            if not force_refresh:
                cache = db.query(SchemaCache).filter_by(
                    datasource_id=datasource_id,
                    is_valid=True
                ).order_by(SchemaCache.updated_at.desc()).first()
                
                if cache and cache.expires_at and cache.expires_at > datetime.utcnow():
                    logger.info(f"使用缓存的 Schema: {datasource_id}")
                    return cache.schema_data
            
            # 从数据库获取 Schema
            with connection_pool_manager.managed_connection(datasource_id) as connector:
                schema_data = connector.get_schema()
                
                # 计算校验和
                schema_json = json.dumps(schema_data, sort_keys=True)
                checksum = hashlib.sha256(schema_json.encode()).hexdigest()
                
                # 统计信息
                table_count = len(schema_data.get('tables', {}))
                column_count = sum(
                    len(table.get('columns', []))
                    for table in schema_data.get('tables', {}).values()
                )
                
                # 识别大表
                large_tables = []
                for table_name, table_info in schema_data.get('tables', {}).items():
                    # 这里可以添加大表识别逻辑
                    if table_info.get('estimated_rows', 0) > 1000000:
                        large_tables.append(table_name)
                
                # 保存到缓存
                cache = SchemaCache(
                    id=hashlib.md5(f"{datasource_id}:{checksum}".encode()).hexdigest(),
                    datasource_id=datasource_id,
                    schema_data=schema_data,
                    table_count=table_count,
                    column_count=column_count,
                    large_tables=large_tables,
                    estimated_total_rows=sum(
                        table.get('estimated_rows', 0)
                        for table in schema_data.get('tables', {}).values()
                    ),
                    version="1.0",
                    checksum=checksum,
                    expires_at=datetime.utcnow() + timedelta(hours=24)  # 24小时过期
                )
                
                # 标记旧缓存为无效
                db.query(SchemaCache).filter_by(datasource_id=datasource_id).update(
                    {'is_valid': False}
                )
                
                db.add(cache)
                db.commit()
                
                logger.info(f"Schema 缓存已更新: {datasource_id}, 表: {table_count}, 列: {column_count}")
                
                return schema_data
                
        except Exception as e:
            logger.error(f"获取 Schema 失败: {e}")
            return None
        finally:
            db.close()
    
    def clear_schema_cache(self, datasource_id: str) -> bool:
        """清除 Schema 缓存"""
        db = get_db()
        try:
            db.query(SchemaCache).filter_by(datasource_id=datasource_id).delete()
            db.commit()
            logger.info(f"Schema 缓存已清除: {datasource_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"清除 Schema 缓存失败: {e}")
            return False
        finally:
            db.close()
    
    def execute_query(
        self, 
        datasource_id: str, 
        sql: str, 
        params: Optional[Dict] = None,
        limit: int = 10000,
        timeout: int = 60
    ) -> Tuple[Optional[List[Dict]], Optional[List[str]], Optional[str]]:
        """执行查询"""
        try:
            with connection_pool_manager.managed_connection(datasource_id) as connector:
                data, columns = connector.execute_query(sql, params, limit, timeout)
                return data, columns, None
                
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            return None, None, str(e)
    
    def get_datasource_stats(self) -> Dict[str, Any]:
        """获取数据源统计"""
        db = get_db()
        try:
            total = db.query(Datasource).count()
            active = db.query(Datasource).filter_by(status='active').count()
            error = db.query(Datasource).filter_by(status='error').count()
            inactive = db.query(Datasource).filter_by(status='inactive').count()
            
            # 按类型统计
            type_stats = {}
            for ds_type in ['mysql', 'postgresql', 'oracle', 'sqlite']:
                count = db.query(Datasource).filter_by(type=ds_type).count()
                if count > 0:
                    type_stats[ds_type] = count
            
            # 连接池统计
            pool_stats = connection_pool_manager.get_stats()
            
            return {
                'total': total,
                'active': active,
                'error': error,
                'inactive': inactive,
                'type_stats': type_stats,
                'pool_stats': pool_stats
            }
            
        except Exception as e:
            logger.error(f"获取数据源统计失败: {e}")
            return {}
        finally:
            db.close()


# 全局数据源服务实例
datasource_service = DatasourceService()
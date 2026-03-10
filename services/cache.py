"""
缓存服务
支持 Redis 和内存缓存
"""
import json
import hashlib
from typing import Optional, Any, Dict, List
from datetime import timedelta
import time

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config.settings import settings


class CacheService:
    """缓存服务"""
    
    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis and REDIS_AVAILABLE
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._redis_client = None
        
        if self.use_redis:
            try:
                self._redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True
                )
                # 测试连接
                self._redis_client.ping()
            except Exception:
                self.use_redis = False
                print("Redis 不可用，使用内存缓存")
    
    def _generate_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值（不存在返回 None）
        """
        if self.use_redis and self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    return json.loads(value)
                return None
            except Exception:
                pass
        
        # 内存缓存
        if key in self._memory_cache:
            cache_entry = self._memory_cache[key]
            if cache_entry["expire"] > time.time():
                return cache_entry["value"]
            else:
                del self._memory_cache[key]
        
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        expire: int = None
    ) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒）
            
        Returns:
            是否成功
        """
        if expire is None:
            expire = settings.CACHE_EXPIRE_SECONDS
        
        if self.use_redis and self._redis_client:
            try:
                self._redis_client.setex(
                    key, 
                    expire, 
                    json.dumps(value, default=str)
                )
                return True
            except Exception:
                pass
        
        # 内存缓存
        self._memory_cache[key] = {
            "value": value,
            "expire": time.time() + expire
        }
        
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if self.use_redis and self._redis_client:
            try:
                self._redis_client.delete(key)
                return True
            except Exception:
                pass
        
        if key in self._memory_cache:
            del self._memory_cache[key]
            return True
        
        return False
    
    def clear(self, pattern: str = "*") -> bool:
        """清除缓存"""
        if self.use_redis and self._redis_client:
            try:
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
                return True
            except Exception:
                pass
        
        self._memory_cache.clear()
        return True
    
    def get_query_cache_key(
        self, 
        sql: str, 
        datasource_id: str, 
        params: Optional[Dict] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> str:
        """
        生成查询缓存键（包含参数和分页信息）
        
        Args:
            sql: SQL 语句
            datasource_id: 数据源ID
            params: 查询参数
            limit: 限制行数
            offset: 偏移量
            
        Returns:
            缓存键
        """
        import json
        
        # 规范化 SQL（去除多余空格和换行）
        sql_normalized = ' '.join(sql.strip().split())
        
        # 构建缓存数据
        cache_data = {
            'sql': sql_normalized,
            'datasource_id': datasource_id,
            'params': params or {},
            'limit': limit,
            'offset': offset
        }
        
        # 生成 JSON 并排序键以确保一致性
        cache_json = json.dumps(cache_data, sort_keys=True, default=str)
        return self._generate_key("query", cache_json)
    
    def cache_query_result(
        self, 
        sql: str, 
        datasource_id: str, 
        result: Dict[str, Any],
        params: Optional[Dict] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        expire: int = None
    ) -> bool:
        """
        缓存查询结果
        
        Args:
            sql: SQL 语句
            datasource_id: 数据源ID
            result: 查询结果
            params: 查询参数
            limit: 限制行数
            offset: 偏移量
            expire: 过期时间（秒）
            
        Returns:
            是否成功
        """
        key = self.get_query_cache_key(sql, datasource_id, params, limit, offset)
        
        # 添加缓存元数据
        cached_result = {
            'data': result,
            'cached_at': time.time(),
            'expire_at': time.time() + (expire or settings.CACHE_EXPIRE_SECONDS),
            'key': key,
            'datasource_id': datasource_id,
            'sql_hash': hashlib.md5(sql.encode()).hexdigest()[:16]
        }
        
        return self.set(key, cached_result, expire)
    
    def get_cached_query(
        self, 
        sql: str, 
        datasource_id: str,
        params: Optional[Dict] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存的查询结果
        
        Args:
            sql: SQL 语句
            datasource_id: 数据源ID
            params: 查询参数
            limit: 限制行数
            offset: 偏移量
            
        Returns:
            缓存结果（不存在返回 None）
        """
        key = self.get_query_cache_key(sql, datasource_id, params, limit, offset)
        cached = self.get(key)
        
        if cached and 'data' in cached:
            return cached['data']
        
        return None
    
    def get_cache_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存信息
        
        Args:
            key: 缓存键
            
        Returns:
            缓存信息
        """
        cached = self.get(key)
        if not cached:
            return None
        
        info = {
            'key': key,
            'cached_at': cached.get('cached_at'),
            'expire_at': cached.get('expire_at'),
            'size': len(str(cached).encode('utf-8')),
            'datasource_id': cached.get('datasource_id'),
            'sql_hash': cached.get('sql_hash')
        }
        
        # 计算剩余时间
        if info['expire_at']:
            info['ttl_seconds'] = max(0, info['expire_at'] - time.time())
        
        return info
    
    def invalidate_query_cache(self, datasource_id: str) -> bool:
        """使数据源的查询缓存失效"""
        return self.clear(f"query:{datasource_id}:*")


# 全局缓存服务实例
cache_service = CacheService()

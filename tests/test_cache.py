"""
缓存服务测试
"""
import pytest
import time
from unittest.mock import Mock, patch

from services.cache import CacheService


class TestCacheService:
    """缓存服务测试"""
    
    def setup_method(self):
        """测试设置"""
        self.cache_service = CacheService(use_redis=False)  # 使用内存缓存
    
    def test_set_and_get(self):
        """测试设置和获取缓存"""
        key = 'test_key'
        value = {'data': 'test_value', 'number': 123}
        
        # 设置缓存
        success = self.cache_service.set(key, value, expire=10)
        assert success is True
        
        # 获取缓存
        cached = self.cache_service.get(key)
        assert cached == value
    
    def test_get_nonexistent(self):
        """测试获取不存在的缓存"""
        cached = self.cache_service.get('nonexistent_key')
        assert cached is None
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        key = 'expiring_key'
        value = 'expiring_value'
        
        # 设置1秒过期的缓存
        self.cache_service.set(key, value, expire=1)
        
        # 立即获取应该存在
        cached = self.cache_service.get(key)
        assert cached == value
        
        # 等待过期
        time.sleep(1.1)
        
        # 再次获取应该不存在
        cached = self.cache_service.get(key)
        assert cached is None
    
    def test_delete(self):
        """测试删除缓存"""
        key = 'to_delete'
        value = 'to_delete_value'
        
        self.cache_service.set(key, value)
        
        # 删除前应该存在
        assert self.cache_service.get(key) == value
        
        # 删除
        success = self.cache_service.delete(key)
        assert success is True
        
        # 删除后应该不存在
        assert self.cache_service.get(key) is None
    
    def test_delete_nonexistent(self):
        """测试删除不存在的缓存"""
        success = self.cache_service.delete('nonexistent_key')
        assert success is False
    
    def test_clear(self):
        """测试清除所有缓存"""
        # 设置多个缓存
        for i in range(5):
            self.cache_service.set(f'key_{i}', f'value_{i}')
        
        # 验证缓存存在
        for i in range(5):
            assert self.cache_service.get(f'key_{i}') == f'value_{i}'
        
        # 清除所有缓存
        success = self.cache_service.clear()
        assert success is True
        
        # 验证缓存已清除
        for i in range(5):
            assert self.cache_service.get(f'key_{i}') is None
    
    def test_generate_key(self):
        """测试生成缓存键"""
        key1 = self.cache_service._generate_key('prefix', 'arg1', 'arg2')
        key2 = self.cache_service._generate_key('prefix', 'arg1', 'arg2')
        key3 = self.cache_service._generate_key('prefix', 'arg2', 'arg1')  # 参数顺序不同
        
        # 相同参数应该生成相同键
        assert key1 == key2
        
        # 参数顺序不同应该生成不同键
        assert key1 != key3
        
        # 键应该是32位十六进制字符串
        assert len(key1) == 32
        assert all(c in '0123456789abcdef' for c in key1)
    
    def test_query_cache_key_with_params(self):
        """测试带参数的查询缓存键"""
        sql = "SELECT * FROM users WHERE age > :age"
        datasource_id = "mysql_demo"
        params = {'age': 18}
        
        key1 = self.cache_service.get_query_cache_key(sql, datasource_id, params)
        key2 = self.cache_service.get_query_cache_key(sql, datasource_id, params)
        
        # 相同查询应该生成相同键
        assert key1 == key2
        
        # 不同参数应该生成不同键
        params2 = {'age': 21}
        key3 = self.cache_service.get_query_cache_key(sql, datasource_id, params2)
        assert key1 != key3
    
    def test_query_cache_key_with_limit_offset(self):
        """测试带分页的查询缓存键"""
        sql = "SELECT * FROM products"
        datasource_id = "pg_demo"
        
        key1 = self.cache_service.get_query_cache_key(sql, datasource_id, limit=10, offset=0)
        key2 = self.cache_service.get_query_cache_key(sql, datasource_id, limit=20, offset=0)
        key3 = self.cache_service.get_query_cache_key(sql, datasource_id, limit=10, offset=10)
        
        # 不同限制和偏移应该生成不同键
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
    
    def test_cache_query_result(self):
        """测试缓存查询结果"""
        sql = "SELECT * FROM test"
        datasource_id = "test_ds"
        result = {
            'success': True,
            'data': [{'id': 1, 'name': 'test'}],
            'columns': ['id', 'name']
        }
        
        # 缓存查询结果
        success = self.cache_service.cache_query_result(sql, datasource_id, result)
        assert success is True
        
        # 获取缓存的查询结果
        cached = self.cache_service.get_cached_query(sql, datasource_id)
        assert cached == result
    
    def test_get_cached_query_nonexistent(self):
        """测试获取不存在的缓存查询"""
        cached = self.cache_service.get_cached_query(
            "SELECT * FROM nonexistent",
            "nonexistent_ds"
        )
        assert cached is None
    
    def test_invalidate_query_cache(self):
        """测试使查询缓存失效"""
        datasource_id = "test_ds"
        
        # 设置多个查询缓存
        for i in range(3):
            sql = f"SELECT * FROM table_{i}"
            result = {'data': [{'id': i}]}
            self.cache_service.cache_query_result(sql, datasource_id, result)
        
        # 验证缓存存在
        for i in range(3):
            sql = f"SELECT * FROM table_{i}"
            cached = self.cache_service.get_cached_query(sql, datasource_id)
            assert cached is not None
        
        # 使该数据源的缓存失效
        success = self.cache_service.invalidate_query_cache(datasource_id)
        assert success is True
        
        # 验证缓存已失效
        for i in range(3):
            sql = f"SELECT * FROM table_{i}"
            cached = self.cache_service.get_cached_query(sql, datasource_id)
            assert cached is None
    
    def test_get_cache_info(self):
        """测试获取缓存信息"""
        key = 'info_test'
        value = {'test': 'data'}
        
        self.cache_service.set(key, value, expire=60)
        
        info = self.cache_service.get_cache_info(key)
        
        assert info is not None
        assert info['key'] == key
        assert 'cached_at' in info
        assert 'expire_at' in info
        assert 'ttl_seconds' in info
        assert info['ttl_seconds'] > 0
    
    def test_get_cache_info_nonexistent(self):
        """测试获取不存在的缓存信息"""
        info = self.cache_service.get_cache_info('nonexistent_key')
        assert info is None
    
    @patch('services.cache.REDIS_AVAILABLE', True)
    @patch('services.cache.redis.Redis')
    def test_redis_fallback(self, mock_redis):
        """测试 Redis 回退到内存缓存"""
        # 模拟 Redis 连接失败
        mock_redis_instance = Mock()
        mock_redis_instance.ping.side_effect = Exception("Redis connection failed")
        mock_redis.return_value = mock_redis_instance
        
        # 创建缓存服务（应该回退到内存缓存）
        cache = CacheService(use_redis=True)
        
        # 测试内存缓存功能
        cache.set('test_key', 'test_value')
        cached = cache.get('test_key')
        
        assert cached == 'test_value'
        assert cache.use_redis is False  # 应该已回退到内存缓存
    
    def test_sql_normalization(self):
        """测试 SQL 规范化"""
        sql1 = "SELECT  *  FROM  users  WHERE  id = 1"
        sql2 = "SELECT * FROM users WHERE id = 1"
        sql3 = """
            SELECT *
            FROM users
            WHERE id = 1
        """
        
        datasource_id = "test_ds"
        
        # 虽然 SQL 格式不同，但经过规范化后应该生成相同的缓存键
        key1 = self.cache_service.get_query_cache_key(sql1, datasource_id)
        key2 = self.cache_service.get_query_cache_key(sql2, datasource_id)
        key3 = self.cache_service.get_query_cache_key(sql3, datasource_id)
        
        assert key1 == key2
        assert key1 == key3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
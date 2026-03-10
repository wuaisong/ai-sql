"""
查询限流和配额管理
防止查询数据过多、资源滥用的保护机制
"""
import time
import uuid
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QuotaType(str, Enum):
    """配额类型"""
    ROWS_PER_QUERY = "rows_per_query"      # 单次查询行数
    ROWS_PER_DAY = "rows_per_day"          # 每日查询行数
    QUERIES_PER_HOUR = "queries_per_hour"  # 每小时查询次数
    EXECUTION_TIME = "execution_time"      # 执行时间
    CONCURRENT_QUERIES = "concurrent"      # 并发查询数


@dataclass
class QuotaConfig:
    """配额配置"""
    # 行数限制
    max_rows_per_query: int = 10000        # 单次查询最大行数
    max_rows_per_day: int = 1000000        # 每日最大行数
    soft_limit_rows: int = 1000            # 软限制（超过警告）
    
    # 频率限制
    max_queries_per_hour: int = 100        # 每小时最大查询数
    max_queries_per_day: int = 10000       # 每日最大查询数
    
    # 时间限制
    max_execution_time_seconds: int = 60   # 最大执行时间
    soft_timeout_seconds: int = 30         # 软超时（警告）
    
    # 并发限制
    max_concurrent_queries: int = 5        # 最大并发查询数
    
    # 大表保护
    large_table_threshold: int = 1000000   # 大表阈值（超过需特殊处理）
    require_where_for_large_tables: bool = True  # 大表强制 WHERE
    
    # 用户级别（可覆盖）
    user_quotas: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class UsageRecord:
    """使用记录"""
    user_id: str
    query_count: int = 0
    total_rows: int = 0
    last_query_time: Optional[datetime] = None
    concurrent_queries: int = 0
    _hourly_start: datetime = field(default_factory=datetime.utcnow)
    _daily_start: datetime = field(default_factory=datetime.utcnow)
    
    def reset_hourly(self):
        """重置小时统计"""
        now = datetime.utcnow()
        if now - self._hourly_start >= timedelta(hours=1):
            self.query_count = 0
            self._hourly_start = now
    
    def reset_daily(self):
        """重置每日统计"""
        now = datetime.utcnow()
        if now - self._daily_start >= timedelta(days=1):
            self.total_rows = 0
            self.query_count = 0
            self._daily_start = now


class QuotaChecker:
    """
    配额检查器
    检查查询是否超出配额限制（支持数据库持久化）
    """
    
    def __init__(self, config: Optional[QuotaConfig] = None):
        self.config = config or QuotaConfig()
        self.user_usage: Dict[str, UsageRecord] = {}
        self._db = None  # 延迟初始化数据库连接
    
    def _get_db(self):
        """获取数据库连接（延迟初始化）"""
        if self._db is None:
            from models.database import get_db
            self._db = get_db()
        return self._db
    
    def get_user_usage(self, user_id: str) -> UsageRecord:
        """获取用户使用记录（从数据库加载）"""
        db = self._get_db()
        
        try:
            from models.database import UsageRecord as UsageRecordModel
            from datetime import datetime, timedelta
            
            now = datetime.utcnow()
            
            # 查找当天的使用记录
            today_start = datetime(now.year, now.month, now.day)
            today_end = today_start + timedelta(days=1)
            
            record = db.query(UsageRecordModel).filter_by(
                user_id=user_id,
                period_type='day',
                period_start=today_start,
                period_end=today_end
            ).first()
            
            if not record:
                # 创建新的使用记录
                record = UsageRecordModel(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    period_type='day',
                    period_start=today_start,
                    period_end=today_end
                )
                db.add(record)
                db.commit()
            
            # 转换为内存对象
            usage_record = UsageRecord(
                user_id=record.user_id,
                query_count=record.query_count,
                total_rows=record.total_rows,
                last_query_time=record.updated_at,
                concurrent_queries=0  # 从内存中获取
            )
            
            # 检查是否需要重置
            usage_record.reset_daily()
            
            # 更新内存缓存
            self.user_usage[user_id] = usage_record
            
            return usage_record
            
        except Exception as e:
            logger.error(f"获取用户使用记录失败: {e}")
            # 回退到内存模式
            if user_id not in self.user_usage:
                self.user_usage[user_id] = UsageRecord(user_id=user_id)
            
            record = self.user_usage[user_id]
            record.reset_daily()
            return record
    
    def check_query_quota(
        self,
        user_id: str,
        estimated_rows: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        检查查询配额
        
        Args:
            user_id: 用户 ID
            estimated_rows: 预估返回行数
            
        Returns:
            (是否允许，拒绝原因，警告信息)
        """
        record = self.get_user_usage(user_id)
        config = self._get_user_config(user_id)
        warnings = {}
        
        # 1. 检查并发查询数
        if record.concurrent_queries >= config.max_concurrent_queries:
            return False, f"并发查询数已达上限 ({config.max_concurrent_queries})", {}
        
        # 2. 检查每小时查询次数
        if record.query_count >= config.max_queries_per_hour:
            return False, f"每小时查询次数已达上限 ({config.max_queries_per_hour})", {}
        
        # 3. 检查每日查询行数
        if estimated_rows:
            if record.total_rows + estimated_rows > config.max_rows_per_day:
                return False, f"每日查询行数已达上限 ({config.max_rows_per_day})", {}
            
            # 软限制警告
            if estimated_rows > config.soft_limit_rows:
                warnings['rows_warning'] = f"查询行数较大 ({estimated_rows})，建议添加过滤条件"
        
        # 4. 检查预估执行时间
        if estimated_rows and estimated_rows > 100000:
            warnings['performance_warning'] = "查询可能较慢，建议优化"
        
        return True, None, warnings
    
    def record_query(
        self,
        user_id: str,
        actual_rows: int,
        execution_time_seconds: float,
        result_size_bytes: int = 0
    ):
        """记录查询使用情况（保存到数据库）"""
        db = self._get_db()
        
        try:
            from models.database import UsageRecord as UsageRecordModel
            from datetime import datetime
            
            now = datetime.utcnow()
            
            # 查找当天的使用记录
            today_start = datetime(now.year, now.month, now.day)
            today_end = today_start + timedelta(days=1)
            
            record = db.query(UsageRecordModel).filter_by(
                user_id=user_id,
                period_type='day',
                period_start=today_start,
                period_end=today_end
            ).first()
            
            if record:
                # 更新现有记录
                record.query_count += 1
                record.total_rows += actual_rows
                record.total_execution_time_ms += execution_time_seconds * 1000
                record.total_result_size_bytes += result_size_bytes
                record.updated_at = now
                
                # 更新并发统计（简化实现）
                record.max_concurrent_queries = max(
                    record.max_concurrent_queries,
                    self.user_usage.get(user_id, UsageRecord(user_id)).concurrent_queries
                )
            else:
                # 创建新记录
                record = UsageRecordModel(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    period_type='day',
                    period_start=today_start,
                    period_end=today_end,
                    query_count=1,
                    total_rows=actual_rows,
                    total_execution_time_ms=execution_time_seconds * 1000,
                    total_result_size_bytes=result_size_bytes,
                    max_concurrent_queries=1
                )
                db.add(record)
            
            db.commit()
            
            # 更新内存缓存
            if user_id in self.user_usage:
                mem_record = self.user_usage[user_id]
                mem_record.query_count += 1
                mem_record.total_rows += actual_rows
                mem_record.last_query_time = now
            
            logger.info(f"用户 {user_id} 查询：{actual_rows} 行，{execution_time_seconds:.2f}s，{result_size_bytes} 字节")
            
        except Exception as e:
            db.rollback()
            logger.error(f"记录查询使用情况失败: {e}")
            
            # 回退到内存模式
            if user_id in self.user_usage:
                record = self.user_usage[user_id]
                record.query_count += 1
                record.total_rows += actual_rows
                record.last_query_time = datetime.utcnow()
    
    def increment_concurrent(self, user_id: str):
        """增加并发计数"""
        record = self.get_user_usage(user_id)
        record.concurrent_queries += 1
    
    def decrement_concurrent(self, user_id: str):
        """减少并发计数"""
        record = self.get_user_usage(user_id)
        record.concurrent_queries = max(0, record.concurrent_queries - 1)
    
    def _get_user_config(self, user_id: str) -> QuotaConfig:
        """获取用户配置（支持覆盖）"""
        if user_id in self.config.user_quotas:
            user_config = self.config.user_quotas[user_id]
            # 创建临时配置
            return QuotaConfig(
                max_rows_per_query=user_config.get('max_rows_per_query', self.config.max_rows_per_query),
                max_rows_per_day=user_config.get('max_rows_per_day', self.config.max_rows_per_day),
                max_queries_per_hour=user_config.get('max_queries_per_hour', self.config.max_queries_per_hour),
                max_execution_time_seconds=user_config.get('max_execution_time_seconds', self.config.max_execution_time_seconds),
            )
        return self.config


class ResultLimiter:
    """
    结果限制器
    对查询结果进行截断和分页
    """
    
    @staticmethod
    def limit_rows(
        data: list,
        max_rows: int = 10000,
        truncate: bool = True
    ) -> Tuple[list, Dict[str, Any]]:
        """
        限制返回行数
        
        Args:
            data: 原始数据
            max_rows: 最大行数
            truncate: 是否截断
            
        Returns:
            (截断后的数据，元信息)
        """
        metadata = {
            'original_rows': len(data),
            'returned_rows': len(data),
            'truncated': False,
            'has_more': False
        }
        
        if len(data) > max_rows:
            metadata['truncated'] = True
            metadata['has_more'] = True
            
            if truncate:
                data = data[:max_rows]
                metadata['returned_rows'] = max_rows
                metadata['truncate_message'] = f"结果已截断至 {max_rows} 行，原始数据 {len(data)} 行"
            else:
                raise ValueError(f"查询结果超出限制 ({len(data)} > {max_rows})")
        
        return data, metadata
    
    @staticmethod
    def paginate(
        data: list,
        page: int = 1,
        page_size: int = 100,
        max_page_size: int = 1000
    ) -> Tuple[list, Dict[str, Any]]:
        """
        分页返回
        
        Args:
            data: 原始数据
            page: 页码（1-based）
            page_size: 每页大小
            max_page_size: 最大每页大小
            
        Returns:
            (当前页数据，分页信息)
        """
        page_size = min(page_size, max_page_size)
        total = len(data)
        total_pages = (total + page_size - 1) // page_size
        
        start = (page - 1) * page_size
        end = min(start + page_size, total)
        
        paginated_data = data[start:end]
        
        pagination = {
            'page': page,
            'page_size': len(paginated_data),
            'total_rows': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None
        }
        
        return paginated_data, pagination


class LargeTableProtector:
    """
    大表保护器
    对大表查询进行特殊处理
    """
    
    def __init__(self, threshold: int = 1000000):
        self.threshold = threshold
        self.table_stats: Dict[str, Dict[str, Any]] = {}
    
    def update_table_stats(
        self,
        table_name: str,
        row_count: int,
        last_updated: Optional[datetime] = None
    ):
        """更新表统计信息"""
        self.table_stats[table_name] = {
            'row_count': row_count,
            'is_large': row_count >= self.threshold,
            'last_updated': last_updated or datetime.utcnow()
        }
    
    def is_large_table(self, table_name: str) -> bool:
        """检查是否为大表"""
        stats = self.table_stats.get(table_name, {})
        return stats.get('is_large', False)
    
    def validate_large_table_query(
        self,
        sql: str,
        tables: list
    ) -> Tuple[bool, Optional[str], list]:
        """
        验证大表查询
        
        Args:
            sql: SQL 语句
            tables: 涉及的表
            
        Returns:
            (是否允许，拒绝原因，警告列表)
        """
        warnings = []
        large_tables = []
        
        for table in tables:
            if self.is_large_table(table):
                large_tables.append(table)
                
                # 检查是否有 WHERE 条件
                if 'WHERE' not in sql.upper():
                    return False, f"大表 '{table}' 查询必须包含 WHERE 条件", []
                
                # 检查是否有限制
                if 'LIMIT' not in sql.upper():
                    warnings.append(f"建议对大表 '{table}' 添加 LIMIT 限制")
                
                # 检查是否有索引提示
                warnings.append(f"表 '{table}' 是大表 ({self.table_stats[table]['row_count']} 行)，请确保使用索引")
        
        return True, None, warnings
    
    def get_table_stats(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表统计信息"""
        return self.table_stats.get(table_name)


class QueryCostEstimator:
    """
    查询成本估算器
    基于 EXPLAIN 分析估算查询成本
    """
    
    def __init__(self, connector=None):
        self.connector = connector
    
    def estimate_cost(self, sql: str) -> Dict[str, Any]:
        """
        估算查询成本
        
        Returns:
            成本估算信息
        """
        estimation = {
            'estimated_rows': None,
            'estimated_cost': None,
            'scan_type': 'unknown',
            'uses_index': None,
            'warnings': []
        }
        
        if not self.connector:
            return estimation
        
        try:
            # 执行 EXPLAIN
            explain_sql = f"EXPLAIN {sql}"
            result = self.connector.execute_query(explain_sql)
            
            # 简单分析 EXPLAIN 结果
            for row in result[0]:
                row_str = str(row).upper()
                
                # 检查扫描类型
                if 'ALL' in row_str:
                    estimation['scan_type'] = 'full_table_scan'
                    estimation['warnings'].append("检测到全表扫描，建议添加索引")
                elif 'INDEX' in row_str:
                    estimation['scan_type'] = 'index_scan'
                    estimation['uses_index'] = True
                elif 'REF' in row_str or 'CONST' in row_str:
                    estimation['scan_type'] = 'indexed_lookup'
                    estimation['uses_index'] = True
                
                # 估算行数
                if 'rows' in str(row).lower():
                    # 尝试提取行数估算
                    pass
            
            # 基于扫描类型估算成本
            if estimation['scan_type'] == 'full_table_scan':
                estimation['estimated_cost'] = 'high'
            elif estimation['scan_type'] == 'index_scan':
                estimation['estimated_cost'] = 'medium'
            else:
                estimation['estimated_cost'] = 'low'
                
        except Exception as e:
            estimation['warnings'].append(f"成本估算失败：{e}")
        
        return estimation


# 全局实例
quota_checker = QuotaChecker()
result_limiter = ResultLimiter()
large_table_protector = LargeTableProtector()
cost_estimator = None  # 需要 connector 初始化

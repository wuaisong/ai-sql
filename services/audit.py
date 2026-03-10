"""
审计日志服务
记录所有查询操作和系统事件
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from config.settings import settings


class AuditLogger:
    """审计日志服务"""
    
    def __init__(self):
        self.enabled = settings.AUDIT_ENABLED
        self.logger = None
        
        if self.enabled:
            self._setup_logger()
    
    def _setup_logger(self):
        """设置日志器"""
        log_path = Path(settings.AUDIT_LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(settings.AUDIT_LOG_FILE)
        file_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 避免重复添加
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
    
    def log_query(
        self,
        user_id: str,
        username: str,
        datasource_id: str,
        datasource_type: str,
        natural_query: str,
        sql: str,
        success: bool,
        row_count: int = 0,
        execution_time_ms: float = 0,
        error: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        记录查询日志
        
        Args:
            user_id: 用户 ID
            username: 用户名
            datasource_id: 数据源 ID
            datasource_type: 数据源类型
            natural_query: 自然语言查询
            sql: 执行的 SQL
            success: 是否成功
            row_count: 结果行数
            execution_time_ms: 执行时间（毫秒）
            error: 错误信息
            ip_address: IP 地址
        """
        if not self.enabled or not self.logger:
            return
        
        log_entry = {
            "event_type": "QUERY",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "username": username,
            "datasource_id": datasource_id,
            "datasource_type": datasource_type,
            "natural_query": natural_query,
            "sql": sql,
            "success": success,
            "row_count": row_count,
            "execution_time_ms": execution_time_ms,
            "error": error,
            "ip_address": ip_address
        }
        
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_login(
        self,
        username: str,
        success: bool,
        ip_address: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """记录登录日志"""
        if not self.enabled or not self.logger:
            return
        
        log_entry = {
            "event_type": "LOGIN",
            "timestamp": datetime.utcnow().isoformat(),
            "username": username,
            "success": success,
            "ip_address": ip_address,
            "reason": reason
        }
        
        if success:
            self.logger.info(json.dumps(log_entry, ensure_ascii=False))
        else:
            self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
    
    def log_permission_denied(
        self,
        user_id: str,
        username: str,
        action: str,
        resource: str,
        ip_address: Optional[str] = None
    ):
        """记录权限拒绝日志"""
        if not self.enabled or not self.logger:
            return
        
        log_entry = {
            "event_type": "PERMISSION_DENIED",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "username": username,
            "action": action,
            "resource": resource,
            "ip_address": ip_address
        }
        
        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
    
    def log_system_event(
        self,
        event_type: str,
        message: str,
        level: str = "INFO",
        details: Optional[Dict[str, Any]] = None
    ):
        """记录系统事件"""
        if not self.enabled or not self.logger:
            return
        
        log_entry = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "details": details or {}
        }
        
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(json.dumps(log_entry, ensure_ascii=False))
    
    def get_query_logs(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取查询日志（简化实现，实际应查询数据库）
        
        Args:
            user_id: 用户 ID 过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            日志列表
        """
        # 这里应该从数据库查询日志
        # 简化实现返回空列表
        return []


# 全局审计日志实例
audit_logger = AuditLogger()

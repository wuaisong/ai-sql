"""
监控中间件
收集系统指标和性能数据
"""
import time
import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import threading
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """请求指标"""
    path: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: str = ""
    error: bool = False


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    request_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0
    p95_response_time_ms: float = 0
    p99_response_time_ms: float = 0
    active_connections: int = 0
    memory_usage_mb: float = 0
    cpu_percent: float = 0


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_samples: int = 10000, aggregation_interval: int = 60):
        self.max_samples = max_samples
        self.aggregation_interval = aggregation_interval  # 秒
        
        self.request_history: deque = deque(maxlen=max_samples)
        self.system_metrics: List[SystemMetrics] = []
        
        self._lock = threading.RLock()
        self._aggregation_thread = None
        self._running = False
        
        # 当前聚合窗口
        self._window_start = datetime.utcnow()
        self._window_requests: List[RequestMetrics] = []
    
    def start(self):
        """启动指标收集器"""
        if not self._running:
            self._running = True
            self._aggregation_thread = threading.Thread(
                target=self._aggregation_loop,
                daemon=True,
                name="MetricsAggregation"
            )
            self._aggregation_thread.start()
            logger.info("指标收集器已启动")
    
    def stop(self):
        """停止指标收集器"""
        self._running = False
        if self._aggregation_thread:
            self._aggregation_thread.join(timeout=5)
        logger.info("指标收集器已停止")
    
    def record_request(self, metrics: RequestMetrics):
        """记录请求指标"""
        with self._lock:
            self.request_history.append(metrics)
            self._window_requests.append(metrics)
    
    def get_recent_requests(self, limit: int = 100) -> List[RequestMetrics]:
        """获取最近请求"""
        with self._lock:
            return list(self.request_history)[-limit:]
    
    def get_system_metrics(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SystemMetrics]:
        """获取系统指标"""
        with self._lock:
            if not start_time and not end_time:
                return self.system_metrics[-100:]  # 返回最近100个
            
            filtered = []
            for metric in self.system_metrics:
                if start_time and metric.timestamp < start_time:
                    continue
                if end_time and metric.timestamp > end_time:
                    continue
                filtered.append(metric)
            
            return filtered
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            recent_requests = list(self.request_history)[-1000:]  # 最近1000个请求
            
            if not recent_requests:
                return {
                    'total_requests': 0,
                    'error_rate': 0,
                    'avg_response_time_ms': 0,
                    'requests_per_minute': 0
                }
            
            total = len(recent_requests)
            errors = sum(1 for r in recent_requests if r.error)
            durations = [r.duration_ms for r in recent_requests]
            
            # 计算请求率（基于时间窗口）
            if len(recent_requests) >= 2:
                time_span = (recent_requests[-1].timestamp - recent_requests[0].timestamp).total_seconds()
                requests_per_minute = (total / max(time_span, 1)) * 60
            else:
                requests_per_minute = 0
            
            return {
                'total_requests': total,
                'error_rate': errors / total if total > 0 else 0,
                'avg_response_time_ms': statistics.mean(durations) if durations else 0,
                'p95_response_time_ms': statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else 0,
                'p99_response_time_ms': statistics.quantiles(durations, n=100)[98] if len(durations) >= 100 else 0,
                'requests_per_minute': requests_per_minute,
                'unique_paths': len(set(r.path for r in recent_requests)),
                'unique_users': len(set(r.user_id for r in recent_requests if r.user_id))
            }
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取端点统计"""
        with self._lock:
            endpoint_stats = {}
            
            for request in self.request_history:
                key = f"{request.method} {request.path}"
                
                if key not in endpoint_stats:
                    endpoint_stats[key] = {
                        'count': 0,
                        'errors': 0,
                        'durations': [],
                        'last_request': request.timestamp
                    }
                
                stats = endpoint_stats[key]
                stats['count'] += 1
                if request.error:
                    stats['errors'] += 1
                stats['durations'].append(request.duration_ms)
                stats['last_request'] = max(stats['last_request'], request.timestamp)
            
            # 计算统计值
            for key, stats in endpoint_stats.items():
                durations = stats['durations']
                stats['avg_duration_ms'] = statistics.mean(durations) if durations else 0
                stats['p95_duration_ms'] = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else 0
                stats['error_rate'] = stats['errors'] / stats['count'] if stats['count'] > 0 else 0
                del stats['durations']  # 移除原始数据
            
            return endpoint_stats
    
    def _aggregation_loop(self):
        """聚合循环"""
        while self._running:
            try:
                time.sleep(self.aggregation_interval)
                self._aggregate_window()
                
            except Exception as e:
                logger.error(f"指标聚合失败: {e}")
    
    def _aggregate_window(self):
        """聚合当前窗口"""
        with self._lock:
            if not self._window_requests:
                return
            
            now = datetime.utcnow()
            window_duration = (now - self._window_start).total_seconds()
            
            # 计算窗口指标
            durations = [r.duration_ms for r in self._window_requests]
            errors = sum(1 for r in self._window_requests if r.error)
            
            system_metric = SystemMetrics(
                timestamp=now,
                request_count=len(self._window_requests),
                error_count=errors,
                avg_response_time_ms=statistics.mean(durations) if durations else 0,
                p95_response_time_ms=statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else 0,
                p99_response_time_ms=statistics.quantiles(durations, n=100)[98] if len(durations) >= 100 else 0,
                requests_per_minute=(len(self._window_requests) / max(window_duration, 1)) * 60
            )
            
            self.system_metrics.append(system_metric)
            
            # 清理旧数据
            if len(self.system_metrics) > 1000:
                self.system_metrics = self.system_metrics[-1000:]
            
            # 重置窗口
            self._window_start = now
            self._window_requests.clear()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """监控中间件"""
    
    def __init__(self, app, metrics_collector: MetricsCollector):
        super().__init__(app)
        self.metrics_collector = metrics_collector
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并收集指标"""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # 计算请求耗时
            duration_ms = (time.time() - start_time) * 1000
            
            # 提取用户信息（如果存在）
            user_id = ""
            if hasattr(request.state, 'user'):
                user_id = request.state.user.get('user_id', '')
            
            # 记录指标
            metrics = RequestMetrics(
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                error=response.status_code >= 400
            )
            
            self.metrics_collector.record_request(metrics)
            
            # 添加监控头
            response.headers["X-Request-Duration"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            # 记录异常请求
            duration_ms = (time.time() - start_time) * 1000
            
            metrics = RequestMetrics(
                path=request.url.path,
                method=request.method,
                status_code=500,
                duration_ms=duration_ms,
                error=True
            )
            
            self.metrics_collector.record_request(metrics)
            
            raise


# 全局指标收集器实例
metrics_collector = MetricsCollector()


def get_metrics_summary() -> Dict[str, Any]:
    """获取指标摘要（API 使用）"""
    return metrics_collector.get_summary()


def get_endpoint_stats() -> Dict[str, Dict[str, Any]]:
    """获取端点统计（API 使用）"""
    return metrics_collector.get_endpoint_stats()


def get_recent_requests(limit: int = 100) -> List[Dict[str, Any]]:
    """获取最近请求（API 使用）"""
    requests = metrics_collector.get_recent_requests(limit)
    return [
        {
            'path': r.path,
            'method': r.method,
            'status_code': r.status_code,
            'duration_ms': r.duration_ms,
            'timestamp': r.timestamp.isoformat(),
            'user_id': r.user_id,
            'error': r.error
        }
        for r in requests
    ]
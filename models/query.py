"""
查询相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class QueryStatus(str, Enum):
    """查询状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueryHistory(BaseModel):
    """查询历史模型"""
    id: str
    user_id: str
    username: str
    datasource_id: str
    natural_query: str
    sql: str
    status: QueryStatus
    row_count: int = 0
    execution_time_ms: float = 0
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryTemplate(BaseModel):
    """查询模板模型"""
    id: str
    name: str
    description: Optional[str] = None
    natural_query_template: str
    sql_template: Optional[str] = None
    datasource_type: str
    parameters: List[Dict[str, Any]] = []
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryFavorite(BaseModel):
    """收藏的查询"""
    id: str
    user_id: str
    query_id: str
    name: str
    natural_query: str
    sql: str
    datasource_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryMetrics(BaseModel):
    """查询指标"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_execution_time_ms: float = 0
    total_rows_returned: int = 0
    cache_hit_rate: float = 0.0
    period_start: datetime
    period_end: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

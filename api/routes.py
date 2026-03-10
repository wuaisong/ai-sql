"""
API 路由定义 - 增强版（包含数据量控制）
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from config.settings import settings
from services.auth import auth_service
from services.cache import cache_service
from services.audit import audit_logger
from services.quota import quota_checker, result_limiter, large_table_protector
from core.agent import DataQueryAgent, AgentConfig, AgentRole
from connectors import MySQLConnector, PostgreSQLConnector


router = APIRouter()
security = HTTPBearer()


# ============ 请求/响应模型 ============

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class QueryRequest(BaseModel):
    natural_query: str
    datasource_id: str
    use_cache: bool = True
    limit: int = Field(default=1000, ge=1, le=10000)  # 限制 1-10000
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)
    enable_truncation: bool = True  # 是否允许截断


class QueryResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: int = 0
    sql: str = ""
    explanation: str = ""
    execution_time_ms: float = 0
    confidence: float = 0.0
    error: Optional[str] = None
    from_cache: bool = False
    
    # 数据量控制信息
    truncation_info: Optional[Dict[str, Any]] = None
    pagination_info: Optional[Dict[str, Any]] = None
    warnings: List[str] = []
    quota_info: Optional[Dict[str, Any]] = None


class DatasourceInfo(BaseModel):
    id: str
    name: str
    type: str
    host: str
    port: int
    database: str
    status: str = "unknown"
    table_count: int = 0
    large_tables: List[str] = []


# ============ 依赖项 ============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """获取当前用户"""
    token = credentials.credentials
    user = auth_service.get_current_user(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_datasource_connector(
    datasource_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取数据源连接器（使用连接池）"""
    from services.connection_pool import connection_pool_manager
    
    try:
        # 检查用户是否有权限访问该数据源
        # 这里可以添加数据源级别的权限控制
        
        # 从连接池获取连接
        return connection_pool_manager.get_connection(datasource_id)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"数据源连接失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据源连接器失败: {str(e)}"
        )


# ============ 路由 ============

@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    user = auth_service.authenticate_user(request.username, request.password)
    
    if not user:
        audit_logger.log_login(
            username=request.username,
            success=False,
            reason="用户名或密码错误"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    access_token = auth_service.create_access_token(
        data={
            "sub": user["user_id"],
            "username": user["username"],
            "role": user["role"]
        }
    )
    
    audit_logger.log_login(
        username=request.username,
        success=True
    )
    
    return LoginResponse(
        access_token=access_token,
        username=user["username"],
        role=user["role"]
    )


@router.get("/auth/me")
async def get_current_user_info(user: Dict[str, Any] = Depends(get_current_user)):
    """获取当前用户信息"""
    # 添加配额信息
    usage = quota_checker.get_user_usage(user["user_id"])
    
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "permissions": user.get("permissions", []),
        "quota_usage": {
            "queries_today": usage.query_count,
            "rows_today": usage.total_rows,
            "concurrent_queries": usage.concurrent_queries
        }
    }


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    connector = Depends(get_datasource_connector)
):
    """
    执行自然语言查询（增强版 - 包含数据量控制）
    """
    start_time = datetime.now()
    user_id = user["user_id"]
    warnings = []
    
    # 1. 配额检查（前置）
    quota_checker.increment_concurrent(user_id)
    
    try:
        allowed, reject_reason, quota_warnings = quota_checker.check_query_quota(
            user_id=user_id,
            estimated_rows=request.limit
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reject_reason
            )
        
        warnings.extend(quota_warnings.values())
        
        # 检查权限
        if not auth_service.check_permission(user, "read"):
            audit_logger.log_permission_denied(
                user_id=user["user_id"],
                username=user["username"],
                action="query",
                resource=request.datasource_id
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有查询权限"
            )
        
        # 2. 尝试从缓存获取
        if request.use_cache:
            cached = cache_service.get_cached_query(
                request.natural_query,
                request.datasource_id
            )
            if cached:
                quota_checker.decrement_concurrent(user_id)
                return QueryResponse(**cached, from_cache=True, warnings=warnings)
        
        # 3. 创建 AI 代理
        agent = DataQueryAgent(
            model=settings.DEEPAGENTS_MODEL,
            api_key=settings.DEEPAGENTS_API_KEY,
            api_base=settings.DEEPAGENTS_API_BASE
        )
        
        # 4. 获取 schema 上下文
        schema = connector.get_schema()
        agent.set_schema_context(schema)
        
        # 5. 更新大表统计
        for table_name, table_info in schema.get("tables", {}).items():
            # 这里可以从数据库获取实际行数
            large_table_protector.update_table_stats(
                table_name=table_name,
                row_count=table_info.get("estimated_rows", 0)
            )
        
        # 6. 生成 SQL
        sql_result = agent.generate_sql(request.natural_query)
        
        if not sql_result.success:
            quota_checker.decrement_concurrent(user_id)
            return QueryResponse(
                success=False,
                error="SQL 生成失败",
                sql="",
                confidence=0,
                warnings=warnings
            )
        
        sql = sql_result.sql
        
        # 7. 验证 SQL
        validation = agent.validate_sql(sql, schema)
        if not validation["valid"]:
            quota_checker.decrement_concurrent(user_id)
            return QueryResponse(
                success=False,
                error=f"SQL 验证失败：{', '.join(validation['issues'])}",
                sql=sql,
                confidence=sql_result.get("confidence", 0),
                warnings=warnings
            )
        
        # 8. 大表保护检查
        tables_involved = sql_result.tables_used or []
        large_allowed, large_reject, large_warnings = large_table_protector.validate_large_table_query(
            sql=sql,
            tables=tables_involved
        )
        
        if not large_allowed:
            quota_checker.decrement_concurrent(user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=large_reject
            )
        
        warnings.extend(large_warnings)
        
        # 9. 执行查询
        connector.connect()
        data, columns = connector.execute_query(
            sql,
            limit=min(request.limit, settings.MAX_QUERY_ROWS),
            timeout=settings.QUERY_TIMEOUT_SECONDS
        )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 10. 结果限制和分页
        truncated_data, truncation_info = result_limiter.limit_rows(
            data=data,
            max_rows=min(request.limit, settings.MAX_QUERY_ROWS),
            truncate=request.enable_truncation
        )
        
        paginated_data, pagination_info = result_limiter.paginate(
            data=truncated_data,
            page=request.page,
            page_size=request.page_size
        )
        
        # 添加截断警告
        if truncation_info['truncated']:
            warnings.append(truncation_info.get('truncate_message', '结果已截断'))
        
        # 11. 记录使用情况
        quota_checker.record_query(
            user_id=user_id,
            actual_rows=len(data),
            execution_time_seconds=execution_time / 1000
        )
        
        quota_checker.decrement_concurrent(user_id)
        
        # 12. 构建响应
        result = QueryResponse(
            success=True,
            data=paginated_data,
            columns=columns,
            row_count=len(paginated_data),
            sql=sql,
            explanation=sql_result.get("explanation", ""),
            execution_time_ms=execution_time,
            confidence=sql_result.get("confidence", 0),
            truncation_info=truncation_info,
            pagination_info=pagination_info,
            warnings=warnings,
            quota_info={
                "rows_used": len(data),
                "rows_remaining": quota_checker.get_user_usage(user_id).total_rows
            }
        )
        
        # 13. 缓存结果
        if request.use_cache:
            cache_service.cache_query_result(
                request.natural_query,
                request.datasource_id,
                result.dict()
            )
        
        # 14. 审计日志
        audit_logger.log_query(
            user_id=user["user_id"],
            username=user["username"],
            datasource_id=request.datasource_id,
            datasource_type=connector.__class__.__name__,
            natural_query=request.natural_query,
            sql=sql,
            success=True,
            row_count=len(data),
            execution_time_ms=execution_time
        )
        
        return result
        
    except HTTPException:
        quota_checker.decrement_concurrent(user_id)
        raise
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        quota_checker.decrement_concurrent(user_id)
        
        audit_logger.log_query(
            user_id=user["user_id"],
            username=user["username"],
            datasource_id=request.datasource_id,
            datasource_type="unknown",
            natural_query=request.natural_query,
            sql="",
            success=False,
            execution_time_ms=execution_time,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询执行失败：{str(e)}"
        )


@router.get("/datasources", response_model=List[DatasourceInfo])
async def list_datasources(user: Dict[str, Any] = Depends(get_current_user)):
    """获取数据源列表（增强版 - 包含大表信息）"""
    datasources = [
        {
            "id": "demo_mysql",
            "name": "MySQL 演示",
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "test",
            "status": "active",
            "table_count": 10,
            "large_tables": ["orders", "users"]
        },
        {
            "id": "demo_pg",
            "name": "PostgreSQL 演示",
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test",
            "status": "active",
            "table_count": 5,
            "large_tables": ["transactions"]
        }
    ]
    
    return datasources


@router.get("/datasources/{datasource_id}/schema")
async def get_datasource_schema(
    datasource_id: str,
    connector = Depends(get_datasource_connector)
):
    """获取数据源 schema 信息（增强版 - 包含表大小）"""
    try:
        connector.connect()
        schema = connector.get_schema()
        
        # 添加表大小信息
        for table_name, table_info in schema.get("tables", {}).items():
            is_large = large_table_protector.is_large_table(table_name)
            table_info["is_large_table"] = is_large
            table_info["large_table_warning"] = (
                "这是大表，查询时请添加 WHERE 条件和 LIMIT" if is_large else None
            )
        
        return schema
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 schema 失败：{str(e)}"
        )


@router.get("/quota/usage")
async def get_quota_usage(user: Dict[str, Any] = Depends(get_current_user)):
    """获取配额使用情况"""
    usage = quota_checker.get_user_usage(user["user_id"])
    config = quota_checker._get_user_config(user["user_id"])
    
    return {
        "user_id": user["user_id"],
        "period": {
            "hourly": {
                "limit": config.max_queries_per_hour,
                "used": usage.query_count,
                "remaining": config.max_queries_per_hour - usage.query_count,
                "resets_in": str(timedelta(hours=1) - (datetime.utcnow() - usage._hourly_start))
            },
            "daily": {
                "rows_limit": config.max_rows_per_day,
                "rows_used": usage.total_rows,
                "rows_remaining": config.max_rows_per_day - usage.total_rows,
                "queries_limit": config.max_queries_per_day,
                "queries_used": usage.query_count,
                "resets_in": str(timedelta(days=1) - (datetime.utcnow() - usage._daily_start))
            }
        },
        "concurrent": {
            "limit": config.max_concurrent_queries,
            "current": usage.concurrent_queries,
            "available": config.max_concurrent_queries - usage.concurrent_queries
        }
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "quota_enabled": True,
            "large_table_protection": True,
            "result_truncation": True,
            "pagination": True
        }
    }


# ============ 数据源管理 API ============

class DatasourceCreateRequest(BaseModel):
    """创建数据源请求"""
    id: str = Field(..., min_length=1, max_length=50, regex=r'^[a-zA-Z0-9_-]+$')
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., regex='^(mysql|postgresql|oracle|sqlite)$')
    host: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    file_path: Optional[str] = None  # SQLite 使用
    pool_size: int = Field(default=5, ge=1, le=50)
    timeout: int = Field(default=30, ge=1, le=300)
    max_rows: int = Field(default=10000, ge=100, le=1000000)
    description: Optional[str] = None
    tags: List[str] = []
    config: Dict[str, Any] = {}


class DatasourceUpdateRequest(BaseModel):
    """更新数据源请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    host: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    file_path: Optional[str] = None
    pool_size: Optional[int] = Field(None, ge=1, le=50)
    timeout: Optional[int] = Field(None, ge=1, le=300)
    max_rows: Optional[int] = Field(None, ge=100, le=1000000)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


@router.get("/datasources")
async def list_datasources(
    user: Dict[str, Any] = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, regex='^(mysql|postgresql|oracle|sqlite)$'),
    status: Optional[str] = Query(None, regex='^(active|inactive|error)$'),
    search: Optional[str] = Query(None, max_length=100)
):
    """列出数据源"""
    # 检查权限
    if not auth_service.check_permission(user, "manage_datasources"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有数据源管理权限"
        )
    
    from services.datasource_service import datasource_service
    
    result = datasource_service.list_datasources(
        page=page,
        page_size=page_size,
        type_filter=type,
        status_filter=status,
        search=search
    )
    
    return result


@router.get("/datasources/{datasource_id}")
async def get_datasource(
    datasource_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取数据源详情"""
    # 检查权限
    if not auth_service.check_permission(user, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有读取权限"
        )
    
    from services.datasource_service import datasource_service
    
    datasource = datasource_service.get_datasource(datasource_id)
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在"
        )
    
    return datasource


@router.post("/datasources")
async def create_datasource(
    request: DatasourceCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """创建数据源"""
    # 检查权限
    if not auth_service.check_permission(user, "manage_datasources"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有数据源管理权限"
        )
    
    from services.datasource_service import datasource_service
    
    success, datasource, message = datasource_service.create_datasource(request.dict())
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # 审计日志
    audit_logger.log_system_event(
        event_type="DATASOURCE_CREATE",
        message=f"用户 {user['username']} 创建数据源 {request.id}",
        level="INFO",
        details={"datasource_id": request.id, "type": request.type}
    )
    
    return {
        "success": True,
        "datasource": datasource,
        "message": message
    }


@router.put("/datasources/{datasource_id}")
async def update_datasource(
    datasource_id: str,
    request: DatasourceUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """更新数据源"""
    # 检查权限
    if not auth_service.check_permission(user, "manage_datasources"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有数据源管理权限"
        )
    
    from services.datasource_service import datasource_service
    
    # 移除空值
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    success, datasource, message = datasource_service.update_datasource(
        datasource_id, update_data
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # 审计日志
    audit_logger.log_system_event(
        event_type="DATASOURCE_UPDATE",
        message=f"用户 {user['username']} 更新数据源 {datasource_id}",
        level="INFO",
        details={"datasource_id": datasource_id}
    )
    
    return {
        "success": True,
        "datasource": datasource,
        "message": message
    }


@router.delete("/datasources/{datasource_id}")
async def delete_datasource(
    datasource_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """删除数据源"""
    # 检查权限
    if not auth_service.check_permission(user, "manage_datasources"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有数据源管理权限"
        )
    
    from services.datasource_service import datasource_service
    
    success, message = datasource_service.delete_datasource(datasource_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # 审计日志
    audit_logger.log_system_event(
        event_type="DATASOURCE_DELETE",
        message=f"用户 {user['username']} 删除数据源 {datasource_id}",
        level="WARNING",
        details={"datasource_id": datasource_id}
    )
    
    return {"success": True, "message": message}


@router.post("/datasources/{datasource_id}/test")
async def test_datasource_connection(
    datasource_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """测试数据源连接"""
    # 检查权限
    if not auth_service.check_permission(user, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有读取权限"
        )
    
    from services.datasource_service import datasource_service
    
    success, message = datasource_service.test_connection(datasource_id)
    
    return {
        "success": success,
        "message": message,
        "datasource_id": datasource_id
    }


@router.get("/datasources/{datasource_id}/schema")
async def get_datasource_schema(
    datasource_id: str,
    refresh: bool = Query(False),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取数据源 Schema"""
    # 检查权限
    if not auth_service.check_permission(user, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有读取权限"
        )
    
    from services.datasource_service import datasource_service
    
    schema = datasource_service.get_schema(datasource_id, force_refresh=refresh)
    
    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="无法获取 Schema"
        )
    
    return schema


@router.get("/datasources/stats")
async def get_datasource_stats(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取数据源统计"""
    # 检查权限
    if not auth_service.check_permission(user, "manage_datasources"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有数据源管理权限"
        )
    
    from services.datasource_service import datasource_service
    
    stats = datasource_service.get_datasource_stats()
    
    return stats


from datetime import timedelta  # 需要在文件顶部导入

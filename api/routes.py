"""
API 路由定义
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from config.settings import settings
from services.auth import auth_service, TokenData
from services.cache import cache_service
from services.audit import audit_logger
from core.agent import DataQueryAgent, QueryResult
from connectors import MySQLConnector, PostgreSQLConnector


router = APIRouter()
security = HTTPBearer()


# ============ 请求/响应模型 ============

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class QueryRequest(BaseModel):
    """查询请求"""
    natural_query: str
    datasource_id: str
    use_cache: bool = True
    limit: int = 1000


class QueryResponse(BaseModel):
    """查询响应"""
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


class DatasourceInfo(BaseModel):
    """数据源信息"""
    id: str
    name: str
    type: str
    host: str
    port: int
    database: str
    status: str = "unknown"


class DatasourceCreate(BaseModel):
    """创建数据源请求"""
    name: str
    type: str  # mysql, postgresql, clickhouse
    host: str
    port: int
    database: str
    username: str
    password: str
    description: Optional[str] = None


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
    """获取数据源连接器（简化实现）"""
    # 实际应从数据库获取数据源配置
    # 这里使用模拟配置
    datasources = {
        "demo_mysql": {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "test",
            "username": "root",
            "password": "root"
        },
        "demo_pg": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test",
            "username": "postgres",
            "password": "postgres"
        }
    }
    
    if datasource_id not in datasources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据源 {datasource_id} 不存在"
        )
    
    config = datasources[datasource_id]
    
    if config["type"] == "mysql":
        return MySQLConnector(**config)
    elif config["type"] == "postgresql":
        return PostgreSQLConnector(**config)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的数据源类型：{config['type']}"
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
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "permissions": user.get("permissions", [])
    }


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    connector = Depends(get_datasource_connector)
):
    """
    执行自然语言查询
    """
    start_time = datetime.now()
    
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
    
    # 尝试从缓存获取
    if request.use_cache:
        cached = cache_service.get_cached_query(
            request.natural_query,
            request.datasource_id
        )
        if cached:
            return QueryResponse(**cached, from_cache=True)
    
    try:
        # 创建 AI 代理
        agent = DataQueryAgent(
            model=settings.DEEPAGENTS_MODEL,
            api_key=settings.DEEPAGENTS_API_KEY,
            api_base=settings.DEEPAGENTS_API_BASE
        )
        
        # 获取 schema 上下文
        schema = connector.get_schema()
        agent.set_schema_context(schema)
        
        # 生成 SQL
        sql_result = agent.generate_sql(request.natural_query)
        
        if not sql_result["success"]:
            return QueryResponse(
                success=False,
                error="SQL 生成失败",
                sql="",
                confidence=0
            )
        
        sql = sql_result["sql"]
        
        # 验证 SQL
        validation = agent.validate_sql(sql, schema)
        if not validation["valid"]:
            return QueryResponse(
                success=False,
                error=f"SQL 验证失败：{', '.join(validation['issues'])}",
                sql=sql,
                confidence=sql_result.get("confidence", 0)
            )
        
        # 执行查询
        connector.connect()
        data, columns = connector.execute_query(
            sql,
            limit=request.limit,
            timeout=settings.QUERY_TIMEOUT_SECONDS
        )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = QueryResponse(
            success=True,
            data=data,
            columns=columns,
            row_count=len(data),
            sql=sql,
            explanation=sql_result.get("explanation", ""),
            execution_time_ms=execution_time,
            confidence=sql_result.get("confidence", 0)
        )
        
        # 缓存结果
        if request.use_cache:
            cache_service.cache_query_result(
                request.natural_query,
                request.datasource_id,
                result.dict()
            )
        
        # 审计日志
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
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
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
    """获取数据源列表"""
    # 实际应从数据库获取
    datasources = [
        {
            "id": "demo_mysql",
            "name": "MySQL 演示",
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "test",
            "status": "active"
        },
        {
            "id": "demo_pg",
            "name": "PostgreSQL 演示",
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test",
            "status": "active"
        }
    ]
    
    return datasources


@router.get("/datasources/{datasource_id}/schema")
async def get_datasource_schema(
    datasource_id: str,
    connector = Depends(get_datasource_connector)
):
    """获取数据源 schema 信息"""
    try:
        connector.connect()
        schema = connector.get_schema()
        return schema
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 schema 失败：{str(e)}"
        )


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

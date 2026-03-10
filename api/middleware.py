"""
API 中间件
"""
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

from config.settings import settings
from services.audit import audit_logger


logger = logging.getLogger(__name__)


async def request_logging_middleware(
    request: Request, 
    call_next: Callable
) -> Response:
    """
    请求日志中间件
    记录所有请求的开始和结束时间
    """
    start_time = time.time()
    
    # 获取客户端 IP
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"请求开始：{request.method} {request.url.path} - IP: {client_ip}")
    
    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        logger.info(
            f"请求完成：{request.method} {request.url.path} - "
            f"状态：{response.status_code} - "
            f"耗时：{process_time:.3f}s"
        )
        
        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        
        logger.error(
            f"请求错误：{request.method} {request.url.path} - "
            f"错误：{str(e)} - "
            f"耗时：{process_time:.3f}s"
        )
        
        raise


async def security_headers_middleware(
    request: Request,
    call_next: Callable
) -> Response:
    """
    安全头中间件
    添加安全相关的 HTTP 头
    """
    response = await call_next(request)
    
    # 添加安全头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


async def cors_middleware(
    request: Request,
    call_next: Callable
) -> Response:
    """
    CORS 中间件（简化实现）
    """
    response = await call_next(request)
    
    # 允许的来源（生产环境应该配置具体域名）
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    
    # 处理 OPTIONS 预检请求
    if request.method == "OPTIONS":
        return Response(status_code=200)
    
    return response


async def error_handler_middleware(
    request: Request,
    call_next: Callable
) -> Response:
    """
    错误处理中间件
    捕获未处理的异常并返回友好的错误响应
    """
    try:
        return await call_next(request)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"未处理的异常：{str(e)}")
        
        # 生产环境不暴露详细错误信息
        if settings.DEBUG:
            detail = str(e)
        else:
            detail = "内部服务器错误"
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": detail,
                "type": type(e).__name__
            }
        )

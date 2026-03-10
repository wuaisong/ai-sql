"""
日志工具
"""
import sys
from pathlib import Path
from loguru import logger as loguru_logger

from config.settings import settings


def setup_logger():
    """设置日志"""
    # 移除默认处理器
    loguru_logger.remove()
    
    # 控制台输出
    loguru_logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 文件输出
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    loguru_logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        rotation="100 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    return loguru_logger


# 全局日志器
logger = setup_logger()

"""
验证工具函数
"""
import re
from typing import Optional, List, Tuple


def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """
    验证 SQL 语句
    
    Args:
        sql: SQL 语句
        
    Returns:
        (是否有效，错误信息)
    """
    if not sql or not sql.strip():
        return False, "SQL 语句不能为空"
    
    sql_upper = sql.strip().upper()
    
    # 检查是否以 SELECT 或 WITH 开头（只读查询）
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "只允许 SELECT 查询"
    
    # 检查危险关键字
    dangerous_keywords = [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", 
        "INSERT", "UPDATE", "REPLACE", "GRANT", "REVOKE"
    ]
    
    for keyword in dangerous_keywords:
        # 使用正则确保匹配完整单词
        if re.search(r'\b' + keyword + r'\b', sql_upper):
            return False, f"检测到危险操作：{keyword}"
    
    return True, None


def validate_table_name(table_name: str) -> Tuple[bool, Optional[str]]:
    """验证表名"""
    if not table_name:
        return False, "表名不能为空"
    
    if len(table_name) > 64:
        return False, "表名过长（最大 64 字符）"
    
    # 只允许字母、数字、下划线
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return False, "表名只能包含字母、数字和下划线"
    
    return True, None


def validate_column_name(column_name: str) -> Tuple[bool, Optional[str]]:
    """验证列名"""
    if not column_name:
        return False, "列名不能为空"
    
    if len(column_name) > 64:
        return False, "列名过长（最大 64 字符）"
    
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', column_name):
        return False, "列名只能包含字母、数字和下划线"
    
    return True, None


def validate_limit(limit: int, max_limit: int = 10000) -> Tuple[bool, Optional[str]]:
    """验证 LIMIT 值"""
    if not isinstance(limit, int):
        return False, "LIMIT 必须是整数"
    
    if limit <= 0:
        return False, "LIMIT 必须大于 0"
    
    if limit > max_limit:
        return False, f"LIMIT 不能超过 {max_limit}"
    
    return True, None


def validate_timeout(timeout: int, max_timeout: int = 300) -> Tuple[bool, Optional[str]]:
    """验证超时时间"""
    if not isinstance(timeout, int):
        return False, "超时时间必须是整数"
    
    if timeout <= 0:
        return False, "超时时间必须大于 0"
    
    if timeout > max_timeout:
        return False, f"超时时间不能超过 {max_timeout} 秒"
    
    return True, None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    清理用户输入
    
    Args:
        text: 原始输入
        max_length: 最大长度
        
    Returns:
        清理后的输入
    """
    if not text:
        return ""
    
    # 截断
    text = text[:max_length]
    
    # 移除可能的 SQL 注入字符（基本防护）
    # 注意：这不能替代参数化查询
    text = text.replace("--", "")
    text = text.replace("/*", "")
    text = text.replace("*/", "")
    text = text.replace(";", "")
    
    return text.strip()


def is_valid_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_username(username: str) -> Tuple[bool, Optional[str]]:
    """验证用户名"""
    if not username:
        return False, "用户名不能为空"
    
    if len(username) < 3:
        return False, "用户名至少 3 个字符"
    
    if len(username) > 32:
        return False, "用户名最多 32 个字符"
    
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return False, "用户名只能包含字母、数字和下划线，且必须以字母开头"
    
    return True, None

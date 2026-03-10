"""
认证授权服务
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from config.settings import settings


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token 数据模型"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None


class UserService:
    """用户服务（模拟，实际应连接数据库）"""
    
    def __init__(self):
        # 模拟用户数据库
        self.users = {
            "admin": {
                "user_id": "1",
                "username": "admin",
                "hashed_password": pwd_context.hash("admin123"),
                "role": "admin",
                "permissions": ["read", "write", "admin"]
            },
            "analyst": {
                "user_id": "2",
                "username": "analyst",
                "hashed_password": pwd_context.hash("analyst123"),
                "role": "analyst",
                "permissions": ["read", "write"]
            },
            "viewer": {
                "user_id": "3",
                "username": "viewer",
                "hashed_password": pwd_context.hash("viewer123"),
                "role": "viewer",
                "permissions": ["read"]
            }
        }
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        return self.users.get(username)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)


class AuthService:
    """认证服务"""
    
    def __init__(self):
        self.user_service = UserService()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        认证用户
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            用户信息（认证失败返回 None）
        """
        user = self.user_service.get_user(username)
        if not user:
            return None
        
        if not self.user_service.verify_password(password, user["hashed_password"]):
            return None
        
        return user
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建访问令牌
        
        Args:
            data: Token 数据
            expires_delta: 过期时间增量
            
        Returns:
            JWT Token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        验证 Token
        
        Args:
            token: JWT Token
            
        Returns:
            Token 数据（验证失败返回 None）
        """
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            role: str = payload.get("role")
            
            if user_id is None:
                return None
            
            return TokenData(
                user_id=user_id,
                username=username,
                role=role
            )
            
        except JWTError:
            return None
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        获取当前用户
        
        Args:
            token: JWT Token
            
        Returns:
            用户信息
        """
        token_data = self.verify_token(token)
        if not token_data:
            return None
        
        return self.user_service.get_user(token_data.username)
    
    def check_permission(self, user: Dict[str, Any], permission: str) -> bool:
        """
        检查用户权限
        
        Args:
            user: 用户信息
            permission: 权限名称
            
        Returns:
            是否有权限
        """
        permissions = user.get("permissions", [])
        return permission in permissions


# 全局认证服务实例
auth_service = AuthService()

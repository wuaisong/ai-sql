"""
认证授权服务
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token 数据模型"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None


class UserService:
    """用户服务（数据库集成）"""
    
    def __init__(self):
        self._db = None  # 延迟初始化
    
    def _get_db(self):
        """获取数据库连接（延迟初始化）"""
        if self._db is None:
            from models.database import get_db
            self._db = get_db()
        return self._db
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """从数据库获取用户信息"""
        db = self._get_db()
        
        try:
            from models.database import User
            
            user = db.query(User).filter_by(username=username, is_active=True).first()
            if not user:
                return None
            
            # 权限映射
            role_permissions = {
                'admin': ['read', 'write', 'admin', 'manage_users', 'manage_datasources'],
                'analyst': ['read', 'write', 'export'],
                'viewer': ['read']
            }
            
            return {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'hashed_password': user.hashed_password,
                'role': user.role,
                'permissions': role_permissions.get(user.role, ['read']),
                'quota_config': user.quota_config or {},
                'is_active': user.is_active
            }
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建用户"""
        db = self._get_db()
        
        try:
            from models.database import User
            import uuid
            
            # 检查用户名是否已存在
            existing = db.query(User).filter_by(username=user_data['username']).first()
            if existing:
                return None
            
            # 创建用户
            user = User(
                id=str(uuid.uuid4()),
                username=user_data['username'],
                email=user_data.get('email'),
                hashed_password=pwd_context.hash(user_data['password']),
                role=user_data.get('role', 'viewer'),
                quota_config=user_data.get('quota_config', {})
            )
            
            db.add(user)
            db.commit()
            
            return self.get_user(user.username)
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建用户失败: {e}")
            return None
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新用户"""
        db = self._get_db()
        
        try:
            from models.database import User
            
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return None
            
            # 更新字段
            if 'password' in update_data:
                user.hashed_password = pwd_context.hash(update_data['password'])
            
            if 'email' in update_data:
                user.email = update_data['email']
            
            if 'role' in update_data:
                user.role = update_data['role']
            
            if 'quota_config' in update_data:
                user.quota_config = update_data['quota_config']
            
            if 'is_active' in update_data:
                user.is_active = update_data['is_active']
            
            db.commit()
            
            return self.get_user(user.username)
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新用户失败: {e}")
            return None


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

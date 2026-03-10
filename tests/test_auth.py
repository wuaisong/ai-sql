"""
认证服务测试
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from services.auth import AuthService, auth_service, pwd_context


class TestAuthService:
    """认证服务测试"""
    
    def setup_method(self):
        """测试设置"""
        self.auth_service = AuthService()
    
    def test_authenticate_user_success(self):
        """测试用户认证成功"""
        # 模拟数据库返回用户
        with patch.object(self.auth_service.user_service, 'get_user') as mock_get_user:
            mock_get_user.return_value = {
                'user_id': 'test-123',
                'username': 'testuser',
                'hashed_password': pwd_context.hash('testpassword'),
                'role': 'viewer',
                'permissions': ['read']
            }
            
            user = self.auth_service.authenticate_user('testuser', 'testpassword')
            
            assert user is not None
            assert user['username'] == 'testuser'
            assert user['role'] == 'viewer'
    
    def test_authenticate_user_wrong_password(self):
        """测试用户认证密码错误"""
        with patch.object(self.auth_service.user_service, 'get_user') as mock_get_user:
            mock_get_user.return_value = {
                'user_id': 'test-123',
                'username': 'testuser',
                'hashed_password': pwd_context.hash('correctpassword'),
                'role': 'viewer',
                'permissions': ['read']
            }
            
            user = self.auth_service.authenticate_user('testuser', 'wrongpassword')
            
            assert user is None
    
    def test_authenticate_user_not_found(self):
        """测试用户不存在"""
        with patch.object(self.auth_service.user_service, 'get_user') as mock_get_user:
            mock_get_user.return_value = None
            
            user = self.auth_service.authenticate_user('nonexistent', 'password')
            
            assert user is None
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        token_data = {
            'sub': 'test-123',
            'username': 'testuser',
            'role': 'viewer'
        }
        
        token = self.auth_service.create_access_token(token_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_valid(self):
        """测试验证有效令牌"""
        token_data = {
            'sub': 'test-123',
            'username': 'testuser',
            'role': 'viewer'
        }
        
        token = self.auth_service.create_access_token(token_data)
        verified = self.auth_service.verify_token(token)
        
        assert verified is not None
        assert verified.user_id == 'test-123'
        assert verified.username == 'testuser'
        assert verified.role == 'viewer'
    
    def test_verify_token_expired(self):
        """测试验证过期令牌"""
        token_data = {
            'sub': 'test-123',
            'username': 'testuser',
            'role': 'viewer'
        }
        
        # 创建立即过期的令牌
        token = self.auth_service.create_access_token(
            token_data, 
            expires_delta=timedelta(seconds=-1)
        )
        
        verified = self.auth_service.verify_token(token)
        
        assert verified is None
    
    def test_verify_token_invalid(self):
        """测试验证无效令牌"""
        verified = self.auth_service.verify_token('invalid.token.here')
        
        assert verified is None
    
    def test_get_current_user_valid(self):
        """测试获取当前用户（有效令牌）"""
        with patch.object(self.auth_service.user_service, 'get_user') as mock_get_user:
            mock_get_user.return_value = {
                'user_id': 'test-123',
                'username': 'testuser',
                'hashed_password': 'hashed',
                'role': 'viewer',
                'permissions': ['read']
            }
            
            token_data = {
                'sub': 'test-123',
                'username': 'testuser',
                'role': 'viewer'
            }
            
            token = self.auth_service.create_access_token(token_data)
            user = self.auth_service.get_current_user(token)
            
            assert user is not None
            assert user['username'] == 'testuser'
    
    def test_check_permission_allowed(self):
        """测试检查权限（允许）"""
        user = {
            'user_id': 'test-123',
            'username': 'testuser',
            'role': 'admin',
            'permissions': ['read', 'write', 'admin']
        }
        
        allowed = self.auth_service.check_permission(user, 'read')
        assert allowed is True
        
        allowed = self.auth_service.check_permission(user, 'admin')
        assert allowed is True
    
    def test_check_permission_denied(self):
        """测试检查权限（拒绝）"""
        user = {
            'user_id': 'test-123',
            'username': 'testuser',
            'role': 'viewer',
            'permissions': ['read']
        }
        
        allowed = self.auth_service.check_permission(user, 'write')
        assert allowed is False
        
        allowed = self.auth_service.check_permission(user, 'admin')
        assert allowed is False
    
    def test_check_permission_no_permissions(self):
        """测试检查权限（无权限列表）"""
        user = {
            'user_id': 'test-123',
            'username': 'testuser',
            'role': 'viewer'
            # 没有 permissions 字段
        }
        
        allowed = self.auth_service.check_permission(user, 'read')
        assert allowed is False


class TestPasswordHashing:
    """密码哈希测试"""
    
    def test_password_hashing(self):
        """测试密码哈希和验证"""
        password = 'MySecurePassword123!'
        
        # 哈希密码
        hashed = pwd_context.hash(password)
        
        # 验证正确密码
        assert pwd_context.verify(password, hashed) is True
        
        # 验证错误密码
        assert pwd_context.verify('WrongPassword', hashed) is False
    
    def test_password_salt_uniqueness(self):
        """测试密码盐值唯一性"""
        password = 'SamePassword'
        
        hashed1 = pwd_context.hash(password)
        hashed2 = pwd_context.hash(password)
        
        # 相同密码应该生成不同的哈希（因为盐值不同）
        assert hashed1 != hashed2
        
        # 但都能验证通过
        assert pwd_context.verify(password, hashed1) is True
        assert pwd_context.verify(password, hashed2) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
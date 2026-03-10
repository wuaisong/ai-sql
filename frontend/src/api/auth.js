import api from './index'

export const authAPI = {
  // 登录
  login(credentials) {
    return api.post('/auth/login', credentials)
  },
  
  // 获取当前用户信息
  getCurrentUser() {
    return api.get('/auth/me')
  },
  
  // 登出
  logout() {
    return api.post('/auth/logout')
  },
  
  // 刷新令牌
  refreshToken(refreshToken) {
    return api.post('/auth/refresh', { refresh_token: refreshToken })
  }
}

export default authAPI
import { defineStore } from 'pinia'
import { authAPI } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    isLoggedIn: !!localStorage.getItem('token')
  }),
  
  getters: {
    username: (state) => state.user?.username || '',
    role: (state) => state.user?.role || '',
    permissions: (state) => state.user?.permissions || []
  },
  
  actions: {
    async login(credentials) {
      const response = await authAPI.login(credentials)
      this.token = response.access_token
      this.user = {
        username: response.username,
        role: response.role,
        permissions: response.permissions || []
      }
      
      localStorage.setItem('token', this.token)
      localStorage.setItem('user', JSON.stringify(this.user))
      this.isLoggedIn = true
      
      return response
    },
    
    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      this.token = ''
      this.user = null
      this.isLoggedIn = false
    },
    
    async fetchCurrentUser() {
      try {
        const response = await authAPI.getCurrentUser()
        this.user = response
        localStorage.setItem('user', JSON.stringify(response))
        return response
      } catch (error) {
        this.logout()
        throw error
      }
    }
  }
})
# Vue 3 前端项目创建指南

## 📦 快速创建

### 方式 1: 使用 Vite（推荐）

```bash
# 1. 创建项目
npm create vite@latest frontend -- --template vue

# 2. 进入目录
cd frontend

# 3. 安装依赖
npm install

# 4. 安装额外依赖
npm install vue-router pinia axios element-plus @element-plus/icons-vue echarts vue-echarts dayjs

# 5. 启动开发服务器
npm run dev
```

### 方式 2: 使用 Vue CLI

```bash
# 1. 安装 Vue CLI
npm install -g @vue/cli

# 2. 创建项目
vue create frontend

# 选择配置：
# - Vue 3
# - Router
# - Pinia
# - ESLint + Prettier

# 3. 进入目录
cd frontend

# 4. 安装额外依赖
npm install axios element-plus @element-plus/icons-vue echarts vue-echarts

# 5. 启动
npm run serve
```

---

## 📁 项目结构

创建以下目录结构：

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API 接口层
│   │   ├── index.js           # axios 实例和拦截器
│   │   ├── auth.js            # 认证 API
│   │   ├── query.js           # 查询 API
│   │   └── datasource.js      # 数据源 API
│   │
│   ├── assets/                 # 静态资源
│   │   └── styles/
│   │       └── variables.scss
│   │
│   ├── components/             # 组件
│   │   ├── common/
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   └── Loading.vue
│   │   ├── query/
│   │   │   ├── QueryEditor.vue
│   │   │   ├── QueryResult.vue
│   │   │   └── SchemaTree.vue
│   │   └── datasource/
│   │       ├── DatasourceList.vue
│   │       └── DatasourceForm.vue
│   │
│   ├── router/                 # 路由配置
│   │   └── index.js
│   │
│   ├── stores/                 # Pinia 状态管理
│   │   ├── user.js
│   │   ├── query.js
│   │   └── datasource.js
│   │
│   ├── views/                  # 页面视图
│   │   ├── Login.vue
│   │   ├── Dashboard.vue
│   │   ├── Query.vue
│   │   ├── Datasources.vue
│   │   └── History.vue
│   │
│   ├── App.vue
│   └── main.js
│
├── .env                        # 环境变量
├── .env.development
├── .env.production
├── package.json
├── vite.config.js
└── README.md
```

---

## 🔧 核心文件代码

### 1. package.json

```json
{
  "name": "enterprise-data-query-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs --fix"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "element-plus": "^2.4.0",
    "@element-plus/icons-vue": "^2.3.0",
    "echarts": "^5.4.0",
    "vue-echarts": "^6.6.0",
    "dayjs": "^1.11.0",
    "lodash-es": "^4.17.21",
    "highlight.js": "^11.9.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.5.0",
    "vite": "^5.0.0",
    "sass": "^1.69.0",
    "eslint": "^8.54.0",
    "eslint-plugin-vue": "^9.18.0"
  }
}
```

---

### 2. vite.config.js

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'echarts': ['echarts']
        }
      }
    }
  }
})
```

---

### 3. src/main.js

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default'
})

app.mount('#app')
```

---

### 4. src/api/index.js

```javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          router.push('/login')
          break
        case 403:
          ElMessage.error('没有权限执行此操作')
          break
        case 429:
          ElMessage.warning('请求过于频繁，请稍后再试')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(error.response.data?.detail || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络连接失败，请检查网络')
    } else {
      ElMessage.error(error.message)
    }
    return Promise.reject(error)
  }
)

export default api
```

---

### 5. src/router/index.js

```javascript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '仪表盘', requiresAuth: true }
  },
  {
    path: '/query',
    name: 'Query',
    component: () => import('@/views/Query.vue'),
    meta: { title: '智能查询', requiresAuth: true }
  },
  {
    path: '/datasources',
    name: 'Datasources',
    component: () => import('@/views/Datasources.vue'),
    meta: { title: '数据源管理', requiresAuth: true }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/History.vue'),
    meta: { title: '查询历史', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '企业级问数系统'}`
  
  const token = localStorage.getItem('token')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
```

---

### 6. src/stores/user.js

```javascript
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
```

---

### 7. src/views/Login.vue

```vue
<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>🔐 企业级问数系统</h2>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        size="large"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            size="large"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-divider />
      
      <el-alert
        title="测试账号"
        type="info"
        :closable="false"
        show-icon
      >
        <template #default>
          <p>管理员：admin / admin123</p>
          <p>分析师：analyst / analyst123</p>
          <p>访客：viewer / viewer123</p>
        </template>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      await userStore.login(form)
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } catch (error) {
      console.error('登录失败:', error)
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 450px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #303133;
}
</style>
```

---

## 🚀 运行步骤

### 1. 创建项目
```bash
npm create vite@latest frontend -- --template vue
cd frontend
npm install
```

### 2. 安装依赖
```bash
npm install vue-router pinia axios element-plus @element-plus/icons-vue
```

### 3. 创建文件结构
按照上面的目录结构创建文件

### 4. 配置环境变量
创建 `.env` 文件：
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=企业级问数系统
```

### 5. 启动开发服务器
```bash
npm run dev
```

**访问**: http://localhost:3000

---

## 📊 功能清单

| 页面 | 功能 | 状态 |
|-----|------|------|
| 登录页 | 用户认证 | ✅ |
| 仪表盘 | 数据统计 | ⏳ |
| 查询页 | 自然语言查询 | ✅ |
| 数据源 | 数据源管理 | ⏳ |
| 查询历史 | 历史记录 | ⏳ |

---

现在你有完整的 **Vue 3 前端项目结构和代码**了！可以直接复制使用。需要我帮你创建具体的某个文件吗？🎉

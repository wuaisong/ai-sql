# 企业级问数系统 - 前端

基于 Vue 3 + Element Plus 的企业级数据查询系统前端。

## 🚀 功能特性

- **智能查询**: 支持自然语言和 SQL 两种查询方式
- **多数据源管理**: 支持 MySQL、PostgreSQL、Oracle、SQLite 等多种数据库
- **数据可视化**: 查询结果图表展示
- **查询历史**: 完整的查询记录和复用功能
- **权限管理**: 基于角色的访问控制
- **响应式设计**: 支持桌面和移动端

## 📁 项目结构

```
frontend/
├── public/                    # 静态资源
├── src/
│   ├── api/                  # API 接口层
│   │   ├── index.js         # axios 实例和拦截器
│   │   ├── auth.js          # 认证 API
│   │   ├── query.js         # 查询 API
│   │   └── datasource.js    # 数据源 API
│   │
│   ├── assets/              # 静态资源
│   │   └── styles/
│   │       └── variables.scss
│   │
│   ├── components/          # 组件
│   │   ├── common/         # 通用组件
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   └── Loading.vue
│   │   ├── query/          # 查询相关组件
│   │   │   ├── QueryEditor.vue
│   │   │   ├── QueryResult.vue
│   │   │   └── SchemaTree.vue
│   │   └── datasource/     # 数据源相关组件
│   │       ├── DatasourceList.vue
│   │       └── DatasourceForm.vue
│   │
│   ├── router/             # 路由配置
│   │   └── index.js
│   │
│   ├── stores/             # Pinia 状态管理
│   │   ├── user.js
│   │   ├── query.js
│   │   └── datasource.js
│   │
│   ├── views/              # 页面视图
│   │   ├── Login.vue
│   │   ├── Dashboard.vue
│   │   ├── Query.vue
│   │   ├── Datasources.vue
│   │   └── History.vue
│   │
│   ├── App.vue
│   └── main.js
│
├── .env                    # 环境变量
├── .env.development
├── .env.production
├── package.json
├── vite.config.js
└── README.md
```

## 🛠️ 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vue Router 4** - 路由管理
- **Pinia** - 状态管理
- **Element Plus** - UI 组件库
- **Axios** - HTTP 客户端
- **Vite** - 构建工具
- **ECharts** - 数据可视化
- **Day.js** - 日期处理

## 📦 安装和运行

### 前提条件

- Node.js 16+ 
- npm 或 yarn

### 安装依赖

```bash
npm install
# 或
yarn install
```

### 开发环境

```bash
npm run dev
# 或
yarn dev
```

访问 http://localhost:3000

### 生产构建

```bash
npm run build
# 或
yarn build
```

构建产物在 `dist` 目录中。

### 预览生产构建

```bash
npm run preview
# 或
yarn preview
```

## 🔧 配置

### 环境变量

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=企业级问数系统
```

### 代理配置

在 `vite.config.js` 中配置代理：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false
    }
  }
}
```

## 📊 页面说明

### 1. 登录页 (`/login`)
- 用户认证
- 测试账号支持

### 2. 仪表盘 (`/dashboard`)
- 系统概览
- 数据统计
- 快速操作

### 3. 智能查询 (`/query`)
- 自然语言查询
- SQL 查询编辑器
- 数据结构浏览
- 查询结果展示

### 4. 数据源管理 (`/datasources`)
- 数据源列表
- 添加/编辑数据源
- 连接测试
- 状态监控

### 5. 查询历史 (`/history`)
- 历史记录查看
- 查询详情
- 结果复用
- 批量操作

## 🔌 API 接口

前端通过以下 API 与后端交互：

### 认证 API
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户
- `POST /api/v1/auth/logout` - 用户登出

### 查询 API
- `POST /api/v1/query/natural` - 自然语言查询
- `POST /api/v1/query/sql` - SQL 查询
- `GET /api/v1/query/history` - 查询历史
- `GET /api/v1/query/saved` - 保存的查询

### 数据源 API
- `GET /api/v1/datasources` - 数据源列表
- `POST /api/v1/datasources` - 创建数据源
- `PUT /api/v1/datasources/:id` - 更新数据源
- `DELETE /api/v1/datasources/:id` - 删除数据源
- `POST /api/v1/datasources/test` - 测试连接

## 🎨 组件说明

### 通用组件
- `AppHeader` - 顶部导航栏
- `AppSidebar` - 侧边栏菜单
- `Loading` - 加载动画

### 查询组件
- `QueryEditor` - 查询编辑器
- `QueryResult` - 查询结果展示
- `SchemaTree` - 数据结构树

### 数据源组件
- `DatasourceList` - 数据源列表
- `DatasourceForm` - 数据源表单

## 📱 响应式设计

系统支持以下断点：

- **移动端**: < 768px
- **平板**: 768px - 992px
- **桌面**: > 992px

## 🔒 权限控制

系统支持三种角色：

1. **管理员** - 所有权限
2. **分析师** - 查询和数据源管理
3. **访客** - 只读查询

## 🐛 常见问题

### 1. 代理配置问题
确保后端服务运行在 `http://localhost:8000`，或修改 `vite.config.js` 中的代理配置。

### 2. 跨域问题
开发环境下使用代理解决，生产环境下需要配置 CORS。

### 3. 样式问题
确保正确引入 Element Plus 样式：
```javascript
import 'element-plus/dist/index.css'
```

### 4. 图标问题
注册所有 Element Plus 图标：
```javascript
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
```

## 📄 许可证

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。

## 📞 支持

如有问题，请查看文档或提交 Issue。
# 企业级问数系统 - 部署指南

## 🚀 快速部署

### 选项1: Docker Compose（推荐）
```bash
# 1. 克隆项目
git clone <repository-url>
cd enterprise-data-query

# 2. 初始化部署
./deploy.sh init

# 3. 启动服务
./deploy.sh start

# 4. 访问应用
# http://localhost:8000
```

### 选项2: 手动部署
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 文件

# 3. 初始化数据库
python migrations.py create
python migrations.py seed

# 4. 启动服务
./start.sh dev
```

## 📋 系统要求

### 最低配置
- CPU: 2 核心
- 内存: 4 GB
- 存储: 10 GB
- 操作系统: Linux/Windows/macOS

### 推荐配置（生产环境）
- CPU: 4+ 核心
- 内存: 8+ GB
- 存储: 50+ GB SSD
- 操作系统: Ubuntu 20.04+/CentOS 8+

## 🔧 配置说明

### 必需配置
```env
# .env 文件
SECRET_KEY=必须设置32位随机字符串
DEEPAGENTS_API_KEY=您的API密钥
```

### 可选配置
```env
# 数据库配置
META_DB_URL=sqlite:///./data/meta.db
# 或 PostgreSQL
# META_DB_URL=postgresql://user:password@localhost:5432/dbname

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=强密码

# 安全配置
DEBUG=false
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 🐳 Docker 部署详情

### 服务架构
```
企业级问数系统
├── app (主应用)       :8000
├── redis (缓存)       :6379
├── mysql-demo (示例)  :3306 (可选)
├── postgres-demo (示例):5432 (可选)
└── nginx (反向代理)   :80/443 (生产环境)
```

### 常用命令
```bash
# 启动所有服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f app

# 重启服务
docker-compose restart app

# 进入容器
docker-compose exec app bash
```

## 🏗️ 生产环境部署

### 步骤1: 准备服务器
```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 安装 Docker Compose
apt install docker-compose -y
```

### 步骤2: 部署应用
```bash
# 创建应用目录
mkdir -p /opt/enterprise-data-query
cd /opt/enterprise-data-query

# 克隆代码
git clone <repository-url> .

# 配置生产环境
cp .env.production .env
# 编辑 .env 文件

# 设置权限
chmod +x deploy.sh start.sh
```

### 步骤3: 启动服务
```bash
# 使用生产配置
docker-compose -f docker-compose.yml --env-file .env up -d

# 验证部署
curl http://localhost:8000/api/v1/system/health
```

### 步骤4: 配置域名和 SSL
```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 获取 SSL 证书
certbot certonly --nginx -d yourdomain.com

# 配置 Nginx
cp nginx.conf /etc/nginx/nginx.conf
systemctl restart nginx
```

## 📊 监控和维护

### 健康检查
```bash
# 手动检查
curl http://localhost:8000/api/v1/system/health

# 自动监控（使用 cron）
*/5 * * * * curl -f http://localhost:8000/api/v1/system/health || systemctl restart docker
```

### 日志管理
```bash
# 查看应用日志
tail -f logs/app.log

# 查看 Docker 日志
docker-compose logs -f

# 日志轮转
# 编辑 /etc/logrotate.d/enterprise-data-query
```

### 备份策略
```bash
# 每日备份（添加到 crontab）
0 2 * * * cd /opt/enterprise-data-query && ./deploy.sh backup

# 备份文件位置
backups/
├── 20240101_020000/
│   ├── mysql_backup.sql
│   ├── postgres_backup.sql
│   ├── data/
│   └── .env
```

## 🔄 更新和升级

### 更新应用
```bash
# 1. 备份当前版本
./deploy.sh backup

# 2. 拉取最新代码
git pull origin main

# 3. 重建镜像
docker-compose build

# 4. 重启服务
docker-compose up -d

# 5. 运行数据库迁移
docker-compose exec app python migrations.py create
```

### 回滚版本
```bash
# 1. 停止当前服务
docker-compose down

# 2. 恢复备份
tar -xzf backups/20240101_020000.tar.gz

# 3. 启动旧版本
git checkout v1.0.0
docker-compose up -d
```

## 🚨 故障排除

### 常见问题

#### 1. 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep :8000

# 修改端口
# 在 .env 中设置 PORT=8001
```

#### 2. 内存不足
```bash
# 查看内存使用
docker stats

# 调整资源限制
# 在 docker-compose.yml 中增加资源限制
```

#### 3. 数据库连接失败
```bash
# 测试连接
docker-compose exec app python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:postgres@postgres-demo:5432/test')
    print('连接成功')
except Exception as e:
    print(f'连接失败: {e}')
"
```

#### 4. Redis 连接失败
```bash
# 检查 Redis
docker-compose exec redis redis-cli ping

# 查看 Redis 日志
docker-compose logs redis
```

### 调试模式
```bash
# 启用调试
export DEBUG=true
export LOG_LEVEL=DEBUG

# 重新启动
docker-compose restart app

# 查看详细日志
docker-compose logs -f app
```

## 📈 性能调优

### 数据库优化
```sql
-- 添加索引
CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_created ON query_history(created_at);

-- 定期清理旧数据
DELETE FROM query_history WHERE created_at < NOW() - INTERVAL '90 days';
```

### 缓存优化
```python
# 调整缓存策略
CACHE_EXPIRE_SECONDS = 600  # 10分钟
QUERY_CACHE_TTL = 7200      # 2小时
```

### 连接池优化
```python
# 增加连接池大小
CONNECTION_POOL_MAX_SIZE = 100
CONNECTION_POOL_IDLE_TIMEOUT = 300
```

## 🔐 安全加固

### 1. 网络安全
```bash
# 配置防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# 限制 Docker 网络
docker network create --internal app-network
```

### 2. 容器安全
```bash
# 使用非 root 用户
docker-compose exec app whoami  # 应该显示 appuser

# 限制容器权限
# 在 docker-compose.yml 中设置 security_opt
```

### 3. 数据加密
```bash
# 加密备份
gpg --symmetric --cipher-algo AES256 backup.tar.gz

# 安全传输
scp -i key.pem backup.tar.gz user@backup-server:/backups/
```

## 📞 支持

### 获取帮助
1. 查看 [README.md](README.md) 文档
2. 检查 [API 文档](http://localhost:8000/docs)
3. 查看系统日志
4. 提交 Issue

### 紧急联系方式
- 系统管理员: admin@example.com
- 技术支持: support@example.com
- 紧急热线: +86-XXX-XXXX-XXXX

---

**部署成功标志**
- ✅ 健康检查通过
- ✅ API 文档可访问
- ✅ 数据库连接正常
- ✅ 缓存服务可用
- ✅ 监控指标正常

**下一步**
1. 配置域名和 SSL
2. 设置监控告警
3. 实施备份策略
4. 进行压力测试
5. 制定应急预案
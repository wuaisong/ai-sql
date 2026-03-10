#!/bin/bash

# 企业级问数系统部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "命令 $1 未找到，请先安装"
        exit 1
    fi
}

# 生成随机密钥
generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

# 初始化部署
init_deploy() {
    log_info "初始化部署..."
    
    # 检查必要命令
    check_command docker
    check_command docker-compose
    check_command python3
    
    # 创建目录
    mkdir -p data logs ssl demo_data
    
    # 生成环境文件
    if [ ! -f .env ]; then
        log_info "创建 .env 文件..."
        cat > .env << EOF
# 应用配置
DEBUG=false
SECRET_KEY=$(generate_secret_key)

# DeepAgents 配置
DEEPAGENTS_API_KEY=${DEEPAGENTS_API_KEY:-}

# Redis 配置
REDIS_PASSWORD=$(generate_secret_key)

# 数据库配置
MYSQL_ROOT_PASSWORD=root
POSTGRES_PASSWORD=postgres
EOF
        log_info ".env 文件已创建，请编辑配置"
    else
        log_info ".env 文件已存在"
    fi
    
    # 创建示例数据初始化脚本
    if [ ! -f demo_data/mysql_init.sql ]; then
        log_info "创建 MySQL 示例数据..."
        cat > demo_data/mysql_init.sql << EOF
-- 创建示例数据库
CREATE DATABASE IF NOT EXISTS test;
USE test;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100),
    age INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建订单表
CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    product_name VARCHAR(100),
    quantity INT,
    price DECIMAL(10, 2),
    order_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 插入示例数据
INSERT INTO users (username, email, age) VALUES
('alice', 'alice@example.com', 25),
('bob', 'bob@example.com', 30),
('charlie', 'charlie@example.com', 35);

INSERT INTO orders (user_id, product_name, quantity, price, order_date) VALUES
(1, 'Laptop', 1, 999.99, '2024-01-15'),
(1, 'Mouse', 2, 29.99, '2024-01-16'),
(2, 'Keyboard', 1, 79.99, '2024-01-17'),
(3, 'Monitor', 1, 299.99, '2024-01-18');
EOF
    fi
    
    if [ ! -f demo_data/postgres_init.sql ]; then
        log_info "创建 PostgreSQL 示例数据..."
        cat > demo_data/postgres_init.sql << EOF
-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100),
    age INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建订单表
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INT,
    product_name VARCHAR(100),
    quantity INT,
    price DECIMAL(10, 2),
    order_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 插入示例数据
INSERT INTO users (username, email, age) VALUES
('alice', 'alice@example.com', 25),
('bob', 'bob@example.com', 30),
('charlie', 'charlie@example.com', 35);

INSERT INTO orders (user_id, product_name, quantity, price, order_date) VALUES
(1, 'Laptop', 1, 999.99, '2024-01-15'),
(1, 'Mouse', 2, 29.99, '2024-01-16'),
(2, 'Keyboard', 1, 79.99, '2024-01-17'),
(3, 'Monitor', 1, 299.99, '2024-01-18');
EOF
    fi
    
    log_info "初始化完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 构建镜像
    docker-compose build
    
    # 启动服务
    docker-compose up -d
    
    # 等待应用启动
    log_info "等待应用启动..."
    sleep 10
    
    # 检查健康状态
    if curl -f http://localhost:8000/api/v1/system/health > /dev/null 2>&1; then
        log_info "应用启动成功"
        log_info "访问地址: http://localhost:8000"
        log_info "API 文档: http://localhost:8000/docs"
    else
        log_error "应用启动失败，请检查日志"
        docker-compose logs app
        exit 1
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose down
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    docker-compose restart
}

# 查看日志
view_logs() {
    service=${1:-app}
    log_info "查看 $service 日志..."
    docker-compose logs -f $service
}

# 数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 进入容器执行迁移
    docker-compose exec app python migrations.py create
    
    # 创建示例数据
    read -p "是否创建示例数据？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose exec app python migrations.py seed
    fi
}

# 备份数据
backup_data() {
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_dir="backups/$timestamp"
    
    log_info "备份数据到 $backup_dir..."
    
    mkdir -p $backup_dir
    
    # 备份数据库
    docker-compose exec -T mysql-demo mysqldump -u root -proot test > $backup_dir/mysql_backup.sql 2>/dev/null || true
    docker-compose exec -T postgres-demo pg_dump -U postgres test > $backup_dir/postgres_backup.sql 2>/dev/null || true
    
    # 备份应用数据
    cp -r data $backup_dir/
    cp -r logs $backup_dir/
    cp .env $backup_dir/
    
    log_info "备份完成"
}

# 显示状态
show_status() {
    log_info "服务状态:"
    docker-compose ps
    
    echo
    log_info "资源使用:"
    docker stats --no-stream
    
    echo
    log_info "应用健康状态:"
    curl -s http://localhost:8000/api/v1/system/health | python3 -m json.tool || echo "应用未运行"
}

# 显示使用说明
show_help() {
    cat << EOF
企业级问数系统部署脚本

使用方法: $0 [命令]

命令:
  init       初始化部署环境
  start      启动所有服务
  stop       停止所有服务
  restart    重启所有服务
  logs       查看日志 [服务名]
  migrate    运行数据库迁移
  backup     备份数据
  status     显示服务状态
  help       显示此帮助信息

示例:
  $0 init     # 初始化部署
  $0 start    # 启动服务
  $0 logs app # 查看应用日志
EOF
}

# 主函数
main() {
    case $1 in
        init)
            init_deploy
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            view_logs $2
            ;;
        migrate)
            run_migrations
            ;;
        backup)
            backup_data
            ;;
        status)
            show_status
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
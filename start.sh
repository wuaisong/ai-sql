#!/bin/bash

# 企业级问数系统启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Python 版本
check_python_version() {
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local required_version="3.9"
    
    if [ $(echo "$python_version >= $required_version" | bc -l) -eq 1 ]; then
        log_info "Python 版本: $python_version ✓"
    else
        log_error "需要 Python $required_version 或更高版本，当前版本: $python_version"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查 Python 包
    local missing_packages=()
    
    for package in fastapi uvicorn sqlalchemy redis; do
        if ! python3 -c "import $package" 2>/dev/null; then
            missing_packages+=($package)
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_warn "缺少 Python 包: ${missing_packages[*]}"
        log_info "正在安装依赖..."
        pip install -r requirements.txt
    else
        log_info "所有依赖已安装 ✓"
    fi
}

# 初始化环境
init_environment() {
    log_info "初始化环境..."
    
    # 创建必要目录
    mkdir -p logs data
    
    # 检查环境文件
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_info "复制环境文件..."
            cp .env.example .env
            log_warn "请编辑 .env 文件配置您的设置"
        else
            log_error "找不到 .env 或 .env.example 文件"
            exit 1
        fi
    fi
    
    # 检查数据库
    if [ ! -f data/meta.db ] && [ ! -f meta.db ]; then
        log_info "初始化数据库..."
        python migrations.py create
        
        read -p "是否创建示例数据？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python migrations.py seed
        fi
    fi
}

# 启动开发服务器
start_dev() {
    log_info "启动开发服务器..."
    
    # 设置环境变量
    export DEBUG=true
    export LOG_LEVEL=DEBUG
    
    # 启动服务器
    uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir . \
        --log-level debug
}

# 启动生产服务器
start_prod() {
    log_info "启动生产服务器..."
    
    # 设置环境变量
    export DEBUG=false
    export LOG_LEVEL=INFO
    
    # 使用 gunicorn 启动多个 worker
    if command -v gunicorn &> /dev/null; then
        gunicorn main:app \
            --workers 4 \
            --worker-class uvicorn.workers.UvicornWorker \
            --bind 0.0.0.0:8000 \
            --access-logfile logs/access.log \
            --error-logfile logs/error.log \
            --log-level info \
            --timeout 120 \
            --keep-alive 5
    else
        log_warn "gunicorn 未安装，使用 uvicorn 单进程模式"
        log_info "建议安装 gunicorn 以获得更好的性能: pip install gunicorn"
        
        uvicorn main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --log-level info \
            --access-log \
            --timeout-keep-alive 5
    fi
}

# 运行测试
run_tests() {
    log_info "运行测试..."
    
    if [ -d "tests" ]; then
        pytest tests/ -v --cov=. --cov-report=html
    else
        log_warn "未找到测试目录"
    fi
}

# 运行代码检查
run_lint() {
    log_info "运行代码检查..."
    
    # 检查 black 是否安装
    if command -v black &> /dev/null; then
        log_info "运行 black 格式化..."
        black . --check
    else
        log_warn "black 未安装，跳过代码格式化检查"
    fi
    
    # 检查 flake8 是否安装
    if command -v flake8 &> /dev/null; then
        log_info "运行 flake8 检查..."
        flake8 .
    else
        log_warn "flake8 未安装，跳过代码风格检查"
    fi
    
    # 检查 mypy 是否安装
    if command -v mypy &> /dev/null; then
        log_info "运行 mypy 类型检查..."
        mypy .
    else
        log_warn "mypy 未安装，跳过类型检查"
    fi
}

# 显示帮助
show_help() {
    cat << EOF
企业级问数系统启动脚本

使用方法: $0 [命令]

命令:
  dev     启动开发服务器（热重载）
  prod    启动生产服务器
  test    运行测试
  lint    运行代码检查
  init    初始化环境
  check   检查依赖和环境
  help    显示此帮助信息

示例:
  $0 init    # 初始化环境
  $0 dev     # 启动开发服务器
  $0 prod    # 启动生产服务器
  $0 test    # 运行测试

环境变量:
  DEBUG         调试模式 (true/false)
  LOG_LEVEL     日志级别 (DEBUG/INFO/WARNING/ERROR)
  PORT          服务端口 (默认: 8000)
EOF
}

# 主函数
main() {
    case $1 in
        dev)
            check_python_version
            check_dependencies
            init_environment
            start_dev
            ;;
        prod)
            check_python_version
            check_dependencies
            init_environment
            start_prod
            ;;
        test)
            check_python_version
            check_dependencies
            run_tests
            ;;
        lint)
            check_python_version
            run_lint
            ;;
        init)
            check_python_version
            check_dependencies
            init_environment
            ;;
        check)
            check_python_version
            check_dependencies
            log_info "环境检查完成 ✓"
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
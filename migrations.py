"""
数据库迁移脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from models.database import init_database, Base, DatabaseManager
from config.settings import settings
import argparse


def create_tables():
    """创建所有表"""
    print("正在创建数据库表...")
    
    db_manager = init_database(settings.META_DB_URL)
    db_manager.create_tables()
    
    print("✅ 数据库表创建完成")


def drop_tables():
    """删除所有表（谨慎使用）"""
    print("⚠️  正在删除所有数据库表...")
    
    confirm = input("确定要删除所有表吗？此操作不可恢复！(输入 'yes' 确认): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return
    
    db_manager = init_database(settings.META_DB_URL)
    db_manager.drop_tables()
    
    print("✅ 数据库表已删除")


def create_sample_data():
    """创建示例数据"""
    print("正在创建示例数据...")
    
    from models.database import get_db
    from datetime import datetime, timedelta
    import uuid
    
    db = get_db()
    
    try:
        # 创建示例用户
        from services.auth import pwd_context
        
        users = [
            {
                'id': str(uuid.uuid4()),
                'username': 'admin',
                'email': 'admin@example.com',
                'hashed_password': pwd_context.hash('admin123'),
                'role': 'admin',
                'quota_config': {'max_rows_per_day': 1000000, 'max_concurrent_queries': 10}
            },
            {
                'id': str(uuid.uuid4()),
                'username': 'analyst',
                'email': 'analyst@example.com',
                'hashed_password': pwd_context.hash('analyst123'),
                'role': 'analyst',
                'quota_config': {'max_rows_per_day': 500000, 'max_concurrent_queries': 5}
            },
            {
                'id': str(uuid.uuid4()),
                'username': 'viewer',
                'email': 'viewer@example.com',
                'hashed_password': pwd_context.hash('viewer123'),
                'role': 'viewer',
                'quota_config': {'max_rows_per_day': 100000, 'max_concurrent_queries': 2}
            }
        ]
        
        # 创建示例数据源
        datasources = [
            {
                'id': 'demo_mysql',
                'name': 'MySQL 演示数据库',
                'type': 'mysql',
                'host': 'localhost',
                'port': 3306,
                'database': 'test',
                'username': 'root',
                'password': 'root',
                'pool_size': 5,
                'timeout': 30,
                'status': 'active',
                'description': 'MySQL 演示数据库，包含示例数据',
                'tags': ['demo', 'mysql']
            },
            {
                'id': 'demo_postgresql',
                'name': 'PostgreSQL 演示数据库',
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database': 'test',
                'username': 'postgres',
                'password': 'postgres',
                'pool_size': 5,
                'timeout': 30,
                'status': 'active',
                'description': 'PostgreSQL 演示数据库',
                'tags': ['demo', 'postgresql']
            }
        ]
        
        # 创建系统配置
        system_configs = [
            {
                'key': 'app.name',
                'value': '企业级问数系统',
                'description': '应用名称',
                'is_system': True
            },
            {
                'key': 'quota.default',
                'value': {
                    'max_rows_per_query': 10000,
                    'max_rows_per_day': 1000000,
                    'max_queries_per_hour': 100,
                    'max_concurrent_queries': 5
                },
                'description': '默认配额配置',
                'is_system': True
            },
            {
                'key': 'security.password_min_length',
                'value': 8,
                'description': '密码最小长度',
                'is_system': True
            }
        ]
        
        # 导入模型
        from models.database import User, Datasource, SystemConfig
        
        # 插入用户
        for user_data in users:
            user = User(**user_data)
            db.add(user)
        
        # 插入数据源
        for ds_data in datasources:
            datasource = Datasource(**ds_data)
            db.add(datasource)
        
        # 插入系统配置
        for config_data in system_configs:
            config = SystemConfig(
                id=str(uuid.uuid4()),
                **config_data
            )
            db.add(config)
        
        db.commit()
        print("✅ 示例数据创建完成")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建示例数据失败: {e}")
        raise
    finally:
        db.close()


def show_tables():
    """显示所有表结构"""
    print("数据库表结构:")
    print("-" * 80)
    
    for table_name, table in Base.metadata.tables.items():
        print(f"\n📊 表名: {table_name}")
        print("字段:")
        for column in table.columns:
            print(f"  - {column.name}: {column.type} {'(PK)' if column.primary_key else ''}")
        
        # 显示索引
        if table.indexes:
            print("索引:")
            for index in table.indexes:
                print(f"  - {index.name}: {[c.name for c in index.columns]}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('command', choices=['create', 'drop', 'seed', 'show', 'reset'],
                       help='迁移命令: create=创建表, drop=删除表, seed=创建示例数据, show=显示表结构, reset=重置数据库')
    
    args = parser.parse_args()
    
    # 初始化数据库连接
    init_database(settings.META_DB_URL)
    
    if args.command == 'create':
        create_tables()
    elif args.command == 'drop':
        drop_tables()
    elif args.command == 'seed':
        create_sample_data()
    elif args.command == 'show':
        show_tables()
    elif args.command == 'reset':
        drop_tables()
        create_tables()
        create_sample_data()
        print("✅ 数据库重置完成")


if __name__ == '__main__':
    main()
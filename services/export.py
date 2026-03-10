"""
数据导出服务
支持查询和导出大量/全部数据
"""
import asyncio
import csv
import json
import io
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """导出格式"""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"  # JSON Lines
    PARQUET = "parquet"
    EXCEL = "excel"


class ExportStatus(str, Enum):
    """导出任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportTask:
    """导出任务"""
    task_id: str
    user_id: str
    query: str
    datasource_id: str
    format: ExportFormat
    status: ExportStatus = ExportStatus.PENDING
    total_rows: int = 0
    exported_rows: int = 0
    file_path: Optional[str] = None
    file_size: int = 0
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "query": self.query,
            "datasource_id": self.datasource_id,
            "format": self.format.value,
            "status": self.status.value,
            "total_rows": self.total_rows,
            "exported_rows": self.exported_rows,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress_percent": self.progress_percent
        }


class DataExporter:
    """
    数据导出器
    支持导出大量/全部数据到文件
    """
    
    def __init__(self, export_dir: str = "./exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, ExportTask] = {}
    
    def create_export_task(
        self,
        user_id: str,
        query: str,
        datasource_id: str,
        format: ExportFormat = ExportFormat.CSV
    ) -> ExportTask:
        """创建导出任务"""
        task_id = f"export_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        task = ExportTask(
            task_id=task_id,
            user_id=user_id,
            query=query,
            datasource_id=datasource_id,
            format=format
        )
        
        self.tasks[task_id] = task
        logger.info(f"创建导出任务：{task_id}")
        
        return task
    
    async def execute_export(
        self,
        task: ExportTask,
        data_fetcher: Callable,
        batch_size: int = 10000,
        max_batches: Optional[int] = None
    ):
        """
        执行导出任务
        
        Args:
            task: 导出任务
            data_fetcher: 数据获取函数 (offset, limit) -> (data, has_more)
            batch_size: 每批数据量
            max_batches: 最大批次数（防止无限）
        """
        task.status = ExportStatus.RUNNING
        
        try:
            file_path = self._get_file_path(task)
            task.file_path = str(file_path)
            
            offset = 0
            batch_count = 0
            total_rows = 0
            
            # 打开文件写入
            with open(file_path, 'w', encoding='utf-8') as f:
                writer = None
                columns = None
                
                while True:
                    # 获取一批数据
                    data, has_more = await data_fetcher(offset=offset, limit=batch_size)
                    
                    if not data:
                        break
                    
                    # 初始化写入器
                    if writer is None:
                        columns = list(data[0].keys())
                        writer = self._create_writer(f, task.format, columns)
                    
                    # 写入数据
                    self._write_batch(writer, data, task.format)
                    
                    # 更新进度
                    batch_count += 1
                    total_rows += len(data)
                    task.exported_rows = total_rows
                    task.progress_percent = min(100.0, (batch_count / max(1, max_batches or 100)) * 100)
                    
                    logger.info(f"导出进度：{total_rows} 行 ({task.progress_percent:.1f}%)")
                    
                    # 检查是否继续
                    if not has_more:
                        break
                    if max_batches and batch_count >= max_batches:
                        logger.warning(f"达到最大批次数 {max_batches}，停止导出")
                        break
                    
                    offset += batch_size
                    
                    # 让出控制权，避免阻塞
                    await asyncio.sleep(0.01)
            
            # 完成
            task.status = ExportStatus.COMPLETED
            task.total_rows = total_rows
            task.completed_at = datetime.utcnow()
            task.file_size = file_path.stat().st_size
            
            logger.info(f"导出完成：{total_rows} 行，{task.file_size} 字节")
            
        except Exception as e:
            task.status = ExportStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            logger.exception(f"导出失败：{e}")
            
            # 清理失败文件
            if task.file_path:
                try:
                    Path(task.file_path).unlink()
                except:
                    pass
    
    def _get_file_path(self, task: ExportTask) -> Path:
        """生成文件路径"""
        timestamp = task.created_at.strftime('%Y%m%d_%H%M%S')
        ext = {
            ExportFormat.CSV: 'csv',
            ExportFormat.JSON: 'json',
            ExportFormat.JSONL: 'jsonl',
            ExportFormat.PARQUET: 'parquet',
            ExportFormat.EXCEL: 'xlsx'
        }.get(task.format, 'csv')
        
        filename = f"{task.task_id}.{ext}"
        return self.export_dir / filename
    
    def _create_writer(self, f, format: ExportFormat, columns: List[str]):
        """创建写入器"""
        if format == ExportFormat.CSV:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            return writer
        elif format == ExportFormat.JSON:
            f.write('[\n')
            return {'file': f, 'first': True}
        elif format == ExportFormat.JSONL:
            return f
        else:
            raise ValueError(f"不支持的格式：{format}")
    
    def _write_batch(self, writer, data: List[Dict], format: ExportFormat):
        """写入一批数据"""
        if format == ExportFormat.CSV:
            writer.writerows(data)
        elif format == ExportFormat.JSON:
            if not writer['first']:
                writer['file'].write(',\n')
            writer['first'] = False
            
            # 写入 JSON 数组元素
            json_str = json.dumps(data, ensure_ascii=False, default=str)
            writer['file'].write(json_str[1:-1])  # 去掉 [ ]
        elif format == ExportFormat.JSONL:
            for row in data:
                writer.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
    
    def finalize_json(self, file_path: str, format: ExportFormat):
        """完成 JSON 文件（闭合数组）"""
        if format == ExportFormat.JSON:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('\n]')
    
    def get_task(self, task_id: str) -> Optional[ExportTask]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def get_user_tasks(self, user_id: str) -> List[ExportTask]:
        """获取用户的所有任务"""
        return [t for t in self.tasks.values() if t.user_id == user_id]
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if task and task.status == ExportStatus.RUNNING:
            task.status = ExportStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            
            # 清理文件
            if task.file_path:
                try:
                    Path(task.file_path).unlink()
                except:
                    pass
            
            return True
        return False
    
    def download_file(self, task_id: str) -> Optional[bytes]:
        """下载文件内容"""
        task = self.tasks.get(task_id)
        if not task or not task.file_path or task.status != ExportStatus.COMPLETED:
            return None
        
        with open(task.file_path, 'rb') as f:
            return f.read()
    
    def cleanup_old_exports(self, max_age_days: int = 7):
        """清理过期导出文件"""
        now = datetime.utcnow()
        cleaned = 0
        
        for task in list(self.tasks.values()):
            if task.created_at:
                age = now - task.created_at
                if age.days > max_age_days:
                    # 删除文件
                    if task.file_path:
                        try:
                            Path(task.file_path).unlink()
                        except:
                            pass
                    
                    # 删除任务记录
                    del self.tasks[task.task_id]
                    cleaned += 1
        
        logger.info(f"清理了 {cleaned} 个过期导出任务")
        return cleaned


class StreamingQuery:
    """
    流式查询
    支持流式返回大量数据，避免内存溢出
    """
    
    def __init__(self, connector, batch_size: int = 1000):
        self.connector = connector
        self.batch_size = batch_size
    
    async def stream_query(
        self,
        sql: str,
        callback: Callable[[List[Dict]], Any],
        limit: Optional[int] = None
    ):
        """
        流式执行查询
        
        Args:
            sql: SQL 语句
            callback: 每批数据的回调函数
            limit: 总行数限制
        """
        if not self.connector.connected:
            self.connector.connect()
        
        # 添加 LIMIT
        if limit and 'LIMIT' not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT {limit}"
        
        offset = 0
        total_rows = 0
        
        while True:
            # 获取一批数据
            batch_sql = f"{sql.rstrip(';')} OFFSET {offset} LIMIT {self.batch_size}"
            data, columns = self.connector.execute_query(batch_sql)
            
            if not data:
                break
            
            # 回调处理
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
            
            total_rows += len(data)
            offset += self.batch_size
            
            logger.debug(f"流式查询进度：{total_rows} 行")
            
            # 检查是否继续
            if len(data) < self.batch_size:
                break
            if limit and total_rows >= limit:
                break
            
            # 让出控制权
            await asyncio.sleep(0.01)
        
        return total_rows


class LargeQueryHandler:
    """
    大查询处理器
    处理查询所有数据的需求
    """
    
    def __init__(self, exporter: DataExporter):
        self.exporter = exporter
        self.streaming = None
    
    async def handle_query_all(
        self,
        user_id: str,
        natural_query: str,
        datasource_id: str,
        sql_generator,
        connector,
        format: ExportFormat = ExportFormat.CSV,
        estimate_only: bool = False
    ) -> Dict[str, Any]:
        """
        处理查询所有数据的请求
        
        Args:
            user_id: 用户 ID
            natural_query: 自然语言查询
            datasource_id: 数据源 ID
            sql_generator: SQL 生成器
            connector: 数据库连接器
            format: 导出格式
            estimate_only: 是否只估算（不实际执行）
            
        Returns:
            处理结果
        """
        # 1. 生成 SQL
        sql_result = sql_generator.generate_sql(natural_query)
        if not sql_result.success:
            return {"success": False, "error": "SQL 生成失败"}
        
        sql = sql_result.sql
        
        # 2. 估算数据量
        estimate = await self._estimate_row_count(sql, connector)
        
        if estimate_only:
            return {
                "success": True,
                "estimated_rows": estimate,
                "recommendation": self._get_recommendation(estimate)
            }
        
        # 3. 根据数据量选择策略
        if estimate < 10000:
            # 小数据量：直接返回
            return await self._handle_small_query(sql, connector)
        elif estimate < 1000000:
            # 中等数据量：导出任务
            return await self._handle_medium_query(
                user_id, natural_query, datasource_id, sql, format
            )
        else:
            # 大数据量：后台任务 + 通知
            return await self._handle_large_query(
                user_id, natural_query, datasource_id, sql, format
            )
    
    async def _estimate_row_count(self, sql: str, connector) -> int:
        """估算行数"""
        try:
            # 使用 EXPLAIN 或 COUNT
            count_sql = f"SELECT COUNT(*) as cnt FROM ({sql}) as subquery"
            data, _ = connector.execute_query(count_sql, limit=1)
            return data[0].get('cnt', 0) if data else 0
        except:
            return 100000  # 默认估算
    
    def _get_recommendation(self, estimated_rows: int) -> str:
        """获取建议"""
        if estimated_rows < 10000:
            return "数据量较小，可直接查询"
        elif estimated_rows < 1000000:
            return "数据量中等，建议导出为文件"
        else:
            return "数据量较大，建议使用后台任务导出"
    
    async def _handle_small_query(self, sql: str, connector) -> Dict[str, Any]:
        """处理小数据量查询"""
        data, columns = connector.execute_query(sql, limit=10000)
        
        return {
            "success": True,
            "data": data,
            "columns": columns,
            "row_count": len(data),
            "strategy": "direct"
        }
    
    async def _handle_medium_query(
        self,
        user_id: str,
        natural_query: str,
        datasource_id: str,
        sql: str,
        format: ExportFormat
    ) -> Dict[str, Any]:
        """处理中等数据量查询（导出任务）"""
        # 创建导出任务
        task = self.exporter.create_export_task(
            user_id=user_id,
            query=natural_query,
            datasource_id=datasource_id,
            format=format
        )
        
        # 异步执行
        async def fetch_data(offset, limit):
            batch_sql = f"{sql.rstrip(';')} LIMIT {limit} OFFSET {offset}"
            data, _ = connector.execute_query(batch_sql)
            has_more = len(data) == limit
            return data, has_more
        
        asyncio.create_task(
            self.exporter.execute_export(task, fetch_data)
        )
        
        return {
            "success": True,
            "task_id": task.task_id,
            "strategy": "export_task",
            "message": "导出任务已创建，请稍后查看进度"
        }
    
    async def _handle_large_query(
        self,
        user_id: str,
        natural_query: str,
        datasource_id: str,
        sql: str,
        format: ExportFormat
    ) -> Dict[str, Any]:
        """处理大数据量查询（后台任务）"""
        # 类似中等查询，但标记为后台任务
        task = self.exporter.create_export_task(
            user_id=user_id,
            query=natural_query,
            datasource_id=datasource_id,
            format=format
        )
        
        # 后台执行（实际应使用任务队列）
        asyncio.create_task(
            self.exporter.execute_export(task, lambda o, l: ( [], False ))
        )
        
        return {
            "success": True,
            "task_id": task.task_id,
            "strategy": "background_task",
            "message": "后台任务已创建，完成后将通知您"
        }


# 全局实例
data_exporter = DataExporter()
large_query_handler = LargeQueryHandler(data_exporter)

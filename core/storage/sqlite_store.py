import aiosqlite
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from utils.logger import get_logger


class SQLiteStore:
    def __init__(self, db_path: str = "llm-os.db"):
        self.db_path = db_path
        self.logger = get_logger(__name__)
    
    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    parameters TEXT,
                    dependencies TEXT,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    result TEXT,
                    error TEXT,
                    metadata TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    tasks TEXT NOT NULL,
                    completed_tasks TEXT,
                    failed_tasks TEXT,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    execution_time REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            await db.commit()
            self.logger.info("SQLite database initialized")
    
    async def save_task(self, task: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO tasks 
                (id, name, action, parameters, dependencies, status, priority,
                 created_at, started_at, completed_at, retry_count, max_retries,
                 result, error, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task['id'],
                task['name'],
                task['action'],
                json.dumps(task.get('parameters', {})),
                json.dumps(task.get('dependencies', [])),
                task['status'],
                task['priority'],
                task['created_at'].isoformat() if isinstance(task['created_at'], datetime) else task['created_at'],
                task['started_at'].isoformat() if task.get('started_at') and isinstance(task['started_at'], datetime) else task.get('started_at'),
                task['completed_at'].isoformat() if task.get('completed_at') and isinstance(task['completed_at'], datetime) else task.get('completed_at'),
                task.get('retry_count', 0),
                task.get('max_retries', 3),
                json.dumps(task.get('result')),
                task.get('error'),
                json.dumps(task.get('metadata', {}))
            ))
            await db.commit()
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks ORDER BY created_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def save_checkpoint(self, checkpoint: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO checkpoints
                (checkpoint_id, graph_id, tasks, completed_tasks, failed_tasks, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint['checkpoint_id'],
                checkpoint['graph_id'],
                json.dumps(checkpoint['tasks']),
                json.dumps(checkpoint.get('completed_tasks', [])),
                json.dumps(checkpoint.get('failed_tasks', [])),
                checkpoint['timestamp'].isoformat() if isinstance(checkpoint['timestamp'], datetime) else checkpoint['timestamp'],
                json.dumps(checkpoint.get('metadata', {}))
            ))
            await db.commit()
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def get_latest_checkpoint(self, graph_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM checkpoints WHERE graph_id = ? ORDER BY timestamp DESC LIMIT 1",
                (graph_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def save_execution_history(self, execution: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO execution_history
                (task_id, status, result, error, execution_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                execution['task_id'],
                execution['status'],
                json.dumps(execution.get('result')),
                execution.get('error'),
                execution.get('execution_time', 0.0),
                execution['timestamp'].isoformat() if isinstance(execution['timestamp'], datetime) else execution['timestamp']
            ))
            await db.commit()
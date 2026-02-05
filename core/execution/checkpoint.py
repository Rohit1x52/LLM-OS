from typing import Dict, List, Any, Optional
from models.task_models import CheckpointData, Task
from core.storage.sqlite_store import SQLiteStore
from core.storage.redis_store import RedisStore
from utils.logger import get_logger
from datetime import datetime
import json


class CheckpointManager:
    def __init__(self, sqlite_store: SQLiteStore, redis_store: RedisStore):
        self.sqlite_store = sqlite_store
        self.redis_store = redis_store
        self.logger = get_logger(__name__)
    
    async def create_checkpoint(
        self,
        graph_id: str,
        tasks: List[Task],
        completed_tasks: List[str],
        failed_tasks: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        checkpoint = CheckpointData(
            graph_id=graph_id,
            tasks=[t.dict() for t in tasks],
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            metadata=metadata or {}
        )
        
        await self.sqlite_store.save_checkpoint(checkpoint.dict())
        
        self.redis_store.set_state(
            f"checkpoint:latest:{graph_id}",
            checkpoint.dict(),
            expire=7200
        )
        
        self.logger.info(f"Created checkpoint {checkpoint.checkpoint_id} for graph {graph_id}")
        return checkpoint.checkpoint_id
    
    async def load_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        checkpoint_dict = await self.sqlite_store.get_checkpoint(checkpoint_id)
        
        if checkpoint_dict:
            return CheckpointData(**checkpoint_dict)
        
        return None
    
    async def load_latest_checkpoint(self, graph_id: str) -> Optional[CheckpointData]:
        cached = self.redis_store.get_state(f"checkpoint:latest:{graph_id}")
        if cached:
            return CheckpointData(**cached)
        
        checkpoint_dict = await self.sqlite_store.get_latest_checkpoint(graph_id)
        
        if checkpoint_dict:
            return CheckpointData(**checkpoint_dict)
        
        return None
    
    async def resume_from_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        checkpoint = await self.load_checkpoint(checkpoint_id)
        
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        tasks = [Task(**t) for t in checkpoint.tasks]
        
        pending_tasks = [
            t for t in tasks
            if t.id not in checkpoint.completed_tasks and t.id not in checkpoint.failed_tasks
        ]
        
        self.logger.info(
            f"Resuming from checkpoint {checkpoint_id}: "
            f"{len(pending_tasks)} tasks remaining"
        )
        
        return {
            'graph_id': checkpoint.graph_id,
            'tasks': tasks,
            'pending_tasks': pending_tasks,
            'completed_tasks': checkpoint.completed_tasks,
            'failed_tasks': checkpoint.failed_tasks,
            'metadata': checkpoint.metadata
        }
    
    async def list_checkpoints(self, graph_id: str) -> List[Dict[str, Any]]:
        all_tasks = await self.sqlite_store.get_all_tasks()
        
        checkpoints = {}
        for task in all_tasks:
            task_data = json.loads(task) if isinstance(task, str) else task
            gid = task_data.get('graph_id')
            if gid and gid == graph_id:
                if gid not in checkpoints:
                    checkpoints[gid] = []
                checkpoints[gid].append(task_data)
        
        return checkpoints.get(graph_id, [])
    
    async def delete_checkpoint(self, checkpoint_id: str):
        self.logger.info(f"Deleting checkpoint {checkpoint_id}")
from typing import Dict, Any, List, Callable, Optional, Awaitable
from models.task_models import Task, TaskStatus
from datetime import datetime
import asyncio


class TaskNode:
    def __init__(self, task: Task):
        self.task = task
        self.children: List['TaskNode'] = []
        self.parents: List['TaskNode'] = []
        self.execution_function: Optional[Callable[[Dict[str, Any]], Awaitable[Any]]] = None
    
    def add_child(self, node: 'TaskNode'):
        if node not in self.children:
            self.children.append(node)
        if self not in node.parents:
            node.parents.append(self)
    
    def add_parent(self, node: 'TaskNode'):
        if node not in self.parents:
            self.parents.append(node)
        if self not in node.children:
            node.children.append(self)
    
    def can_execute(self) -> bool:
        if self.task.status != TaskStatus.PENDING:
            return False
        
        for parent in self.parents:
            if parent.task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def set_execution_function(self, func: Callable[[Dict[str, Any]], Awaitable[Any]]):
        self.execution_function = func
    
    async def execute(self) -> Any:
        if not self.execution_function:
            raise ValueError(f"No execution function set for task {self.task.id}")
        
        self.task.status = TaskStatus.RUNNING
        self.task.started_at = datetime.utcnow()
        
        try:
            result = await self.execution_function(self.task.parameters)
            self.task.result = result
            self.task.status = TaskStatus.COMPLETED
            self.task.completed_at = datetime.utcnow()
            return result
        except Exception as e:
            self.task.error = str(e)
            self.task.status = TaskStatus.FAILED
            self.task.completed_at = datetime.utcnow()
            raise
    
    def get_depth(self) -> int:
        if not self.parents:
            return 0
        return max(parent.get_depth() for parent in self.parents) + 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task': self.task.dict(),
            'children_ids': [child.task.id for child in self.children],
            'parents_ids': [parent.task.id for parent in self.parents],
            'can_execute': self.can_execute()
        }
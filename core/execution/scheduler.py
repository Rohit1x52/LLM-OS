from typing import List, Dict, Any, Optional
from models.task_models import Task, TaskPriority, TaskStatus
from core.execution.task_node import TaskNode
from core.execution.resource_manager import ResourceManager
from utils.logger import get_logger
from datetime import datetime
import asyncio


class Scheduler:
    def __init__(self, resource_manager: ResourceManager):
        self.resource_manager = resource_manager
        self.logger = get_logger(__name__)
        self.priority_weights = {
            TaskPriority.URGENT: 1.0,
            TaskPriority.HIGH: 0.8,
            TaskPriority.NORMAL: 0.5,
            TaskPriority.LOW: 0.3,
            TaskPriority.BACKGROUND: 0.1
        }
    
    def prioritize_tasks(self, tasks: List[TaskNode]) -> List[TaskNode]:
        def task_score(node: TaskNode) -> float:
            priority_score = self.priority_weights.get(node.task.priority, 0.5)
            
            depth_penalty = node.get_depth() * 0.1
            
            dependency_bonus = len(node.children) * 0.05
            
            age_bonus = 0.0
            if node.task.created_at:
                age_minutes = (datetime.utcnow() - node.task.created_at).total_seconds() / 60
                age_bonus = min(age_minutes * 0.01, 0.3)
            
            total_score = priority_score + dependency_bonus + age_bonus - depth_penalty
            return total_score
        
        return sorted(tasks, key=task_score, reverse=True)
    
    def create_execution_plan(self, tasks: List[TaskNode]) -> Dict[str, Any]:
        prioritized = self.prioritize_tasks(tasks)
        
        sequential_tasks = []
        parallel_batches = []
        
        current_batch = []
        current_depth = None
        
        for task in prioritized:
            depth = task.get_depth()
            
            if current_depth is None:
                current_depth = depth
                current_batch = [task]
            elif depth == current_depth:
                current_batch.append(task)
            else:
                if len(current_batch) == 1:
                    sequential_tasks.append(current_batch[0])
                else:
                    parallel_batches.append(current_batch)
                
                current_depth = depth
                current_batch = [task]
        
        if current_batch:
            if len(current_batch) == 1:
                sequential_tasks.append(current_batch[0])
            else:
                parallel_batches.append(current_batch)
        
        return {
            'sequential_tasks': [t.task.id for t in sequential_tasks],
            'parallel_batches': [[t.task.id for t in batch] for batch in parallel_batches],
            'total_tasks': len(tasks),
            'estimated_parallel_speedup': self._estimate_speedup(parallel_batches)
        }
    
    def _estimate_speedup(self, parallel_batches: List[List[TaskNode]]) -> float:
        if not parallel_batches:
            return 1.0
        
        sequential_time = sum(len(batch) for batch in parallel_batches)
        parallel_time = len(parallel_batches)
        
        return sequential_time / parallel_time if parallel_time > 0 else 1.0
    
    async def should_throttle(self, task: Task) -> bool:
        resource_type = self._get_resource_type(task)
        
        if resource_type:
            can_acquire = await self.resource_manager.acquire_resource(resource_type, 1)
            if not can_acquire:
                self.logger.warning(f"Throttling task {task.id} due to resource limits")
                return True
        
        return False
    
    def _get_resource_type(self, task: Task) -> Optional[str]:
        action_to_resource = {
            'api_call': 'api_calls',
            'file_read': 'file_operations',
            'file_write': 'file_operations',
            'database_query': 'database_connections',
            'http_request': 'network_requests',
            'compute': 'cpu_intensive'
        }
        
        return action_to_resource.get(task.action)
    
    def get_next_executable_batch(self, tasks: List[TaskNode], max_parallel: int = 5) -> List[TaskNode]:
        executable = [t for t in tasks if t.can_execute()]
        prioritized = self.prioritize_tasks(executable)
        
        return prioritized[:max_parallel]
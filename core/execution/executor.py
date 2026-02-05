from typing import Dict, List, Any, Callable, Awaitable, Optional
from models.task_models import Task, TaskStatus, ExecutionResult
from core.execution.task_graph import TaskGraph
from core.execution.task_node import TaskNode
from core.execution.state_machine import StateMachine, GraphState
from core.execution.scheduler import Scheduler
from core.execution.retry_handler import RetryHandler
from core.execution.checkpoint import CheckpointManager
from core.execution.resource_manager import ResourceManager
from core.storage.sqlite_store import SQLiteStore
from core.storage.redis_store import RedisStore
from utils.logger import get_logger
import asyncio
from datetime import datetime
import time


class Executor:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.resource_manager = ResourceManager()
        self.retry_handler = RetryHandler()
        self.sqlite_store = SQLiteStore()
        self.redis_store = RedisStore()
        self.checkpoint_manager = CheckpointManager(self.sqlite_store, self.redis_store)
        self.scheduler = Scheduler(self.resource_manager)
        
        self.tool_registry: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}
    
    async def initialize(self):
        await self.sqlite_store.initialize()
        self.logger.info("Executor initialized")
    
    def register_tool(self, action: str, func: Callable[[Dict[str, Any]], Awaitable[Any]]):
        self.tool_registry[action] = func
        self.logger.info(f"Registered tool for action: {action}")
    
    async def execute_graph(self, graph: TaskGraph) -> Dict[str, Any]:
        state_machine = StateMachine(graph.graph_id)
        state_machine.transition_to(GraphState.PLANNING)
        
        for node in graph.nodes.values():
            if node.task.action in self.tool_registry:
                node.set_execution_function(self.tool_registry[node.task.action])
        
        execution_plan = self.scheduler.create_execution_plan(list(graph.nodes.values()))
        self.logger.info(f"Execution plan created: {execution_plan}")
        
        state_machine.transition_to(GraphState.EXECUTING)
        
        results = []
        completed_tasks = []
        failed_tasks = []
        
        try:
            while not graph.is_complete():
                executable_nodes = graph.get_executable_tasks()
                
                if not executable_nodes:
                    pending = [n for n in graph.nodes.values() if n.task.status == TaskStatus.PENDING]
                    if pending:
                        self.logger.error("No executable tasks but graph not complete - possible deadlock")
                        break
                    break
                
                batch = self.scheduler.get_next_executable_batch(executable_nodes, max_parallel=5)
                
                batch_results = await asyncio.gather(
                    *[self._execute_task(node) for node in batch],
                    return_exceptions=True
                )
                
                for node, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        failed_tasks.append(node.task.id)
                        self.logger.error(f"Task {node.task.id} failed: {result}")
                    else:
                        completed_tasks.append(node.task.id)
                        results.append(result)
                
                await self.checkpoint_manager.create_checkpoint(
                    graph.graph_id,
                    list(n.task for n in graph.nodes.values()),
                    completed_tasks,
                    failed_tasks
                )
                
                await asyncio.sleep(0.1)
            
            if failed_tasks:
                state_machine.transition_to(GraphState.FAILED)
            else:
                state_machine.transition_to(GraphState.COMPLETED)
            
        except Exception as e:
            self.logger.error(f"Graph execution failed: {e}")
            state_machine.transition_to(GraphState.FAILED)
            raise
        
        return {
            'graph_id': graph.graph_id,
            'state': state_machine.get_current_state().value,
            'results': results,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'status_summary': graph.get_status_summary(),
            'execution_plan': execution_plan
        }
    
    async def _execute_task(self, node: TaskNode) -> ExecutionResult:
        task = node.task
        start_time = time.time()
        
        self.logger.info(f"Executing task {task.id}: {task.action}")
        
        await self.sqlite_store.save_task(task.dict())
        
        should_throttle = await self.scheduler.should_throttle(task)
        if should_throttle:
            await asyncio.sleep(1.0)
        
        try:
            result = await self.retry_handler.execute_with_retry(
                task.id,
                node.execute
            )
            
            execution_time = time.time() - start_time
            
            execution_result = ExecutionResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time
            )
            
            await self.sqlite_store.save_task(task.dict())
            await self.sqlite_store.save_execution_history(execution_result.dict())
            
            return execution_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.logger.error(f"Task {task.id} failed: {e}")
            
            execution_result = ExecutionResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )
            
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await self.sqlite_store.save_task(task.dict())
            await self.sqlite_store.save_execution_history(execution_result.dict())
            
            raise
    
    async def pause_execution(self, graph_id: str):
        self.logger.info(f"Pausing execution of graph {graph_id}")
    
    async def resume_execution(self, checkpoint_id: str) -> Dict[str, Any]:
        resume_data = await self.checkpoint_manager.resume_from_checkpoint(checkpoint_id)
        
        graph = TaskGraph(resume_data['graph_id'])
        for task in resume_data['tasks']:
            graph.add_task(task)
        
        return await self.execute_graph(graph)
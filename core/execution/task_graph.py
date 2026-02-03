from typing import Dict, List, Any, Optional
from models.task_models import Task, TaskStatus, TaskPriority
from core.execution.task_node import TaskNode
from utils.logger import get_logger
import uuid
import networkx as nx


class TaskGraph:
    def __init__(self, graph_id: Optional[str] = None):
        self.graph_id = graph_id or str(uuid.uuid4())
        self.nodes: Dict[str, TaskNode] = {}
        self.logger = get_logger(__name__)
        self.nx_graph = nx.DiGraph()
    
    def add_task(self, task: Task) -> TaskNode:
        if task.id in self.nodes:
            self.logger.warning(f"Task {task.id} already exists in graph")
            return self.nodes[task.id]
        
        node = TaskNode(task)
        self.nodes[task.id] = node
        self.nx_graph.add_node(task.id, task=task)
        self.logger.info(f"Added task {task.id} to graph")
        return node
    
    def add_dependency(self, parent_task_id: str, child_task_id: str):
        if parent_task_id not in self.nodes:
            raise ValueError(f"Parent task {parent_task_id} not found")
        if child_task_id not in self.nodes:
            raise ValueError(f"Child task {child_task_id} not found")
        
        parent_node = self.nodes[parent_task_id]
        child_node = self.nodes[child_task_id]
        
        parent_node.add_child(child_node)
        self.nx_graph.add_edge(parent_task_id, child_task_id)
        self.logger.info(f"Added dependency: {parent_task_id} -> {child_task_id}")
    
    def get_executable_tasks(self) -> List[TaskNode]:
        executable = []
        for node in self.nodes.values():
            if node.can_execute():
                executable.append(node)
        return executable
    
    def get_tasks_by_priority(self) -> List[TaskNode]:
        priority_order = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
            TaskPriority.BACKGROUND: 4
        }
        
        return sorted(
            self.nodes.values(),
            key=lambda n: (priority_order.get(n.task.priority, 999), n.get_depth())
        )
    
    def get_parallel_groups(self) -> List[List[TaskNode]]:
        groups = []
        processed = set()
        
        for node in self.get_tasks_by_priority():
            if node.task.id in processed:
                continue
            
            if not node.can_execute():
                continue
            
            group = [node]
            depth = node.get_depth()
            
            for other_node in self.nodes.values():
                if other_node.task.id in processed:
                    continue
                if other_node.task.id == node.task.id:
                    continue
                if other_node.get_depth() == depth and other_node.can_execute():
                    group.append(other_node)
            
            for n in group:
                processed.add(n.task.id)
            
            groups.append(group)
        
        return groups
    
    def has_cycles(self) -> bool:
        try:
            cycles = list(nx.simple_cycles(self.nx_graph))
            return len(cycles) > 0
        except:
            return False
    
    def get_topological_order(self) -> List[str]:
        try:
            return list(nx.topological_sort(self.nx_graph))
        except nx.NetworkXError:
            self.logger.error("Graph has cycles, cannot determine topological order")
            return []
    
    def get_critical_path(self) -> List[str]:
        if not self.nodes:
            return []
        
        def get_path_length(node_id: str, memo: Dict[str, int]) -> int:
            if node_id in memo:
                return memo[node_id]
            
            node = self.nodes[node_id]
            if not node.children:
                memo[node_id] = 1
                return 1
            
            max_child_length = max(
                get_path_length(child.task.id, memo)
                for child in node.children
            )
            memo[node_id] = max_child_length + 1
            return memo[node_id]
        
        memo = {}
        root_nodes = [n for n in self.nodes.values() if not n.parents]
        
        if not root_nodes:
            return []
        
        critical_root = max(root_nodes, key=lambda n: get_path_length(n.task.id, memo))
        
        path = []
        current = critical_root
        while current:
            path.append(current.task.id)
            if not current.children:
                break
            current = max(current.children, key=lambda n: get_path_length(n.task.id, memo))
        
        return path
    
    def get_status_summary(self) -> Dict[str, int]:
        summary = {
            TaskStatus.PENDING: 0,
            TaskStatus.RUNNING: 0,
            TaskStatus.COMPLETED: 0,
            TaskStatus.FAILED: 0,
            TaskStatus.RETRYING: 0,
            TaskStatus.CANCELLED: 0,
            TaskStatus.PAUSED: 0
        }
        
        for node in self.nodes.values():
            summary[node.task.status] += 1
        
        return summary
    
    def is_complete(self) -> bool:
        for node in self.nodes.values():
            if node.task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'graph_id': self.graph_id,
            'nodes': {task_id: node.to_dict() for task_id, node in self.nodes.items()},
            'status_summary': self.get_status_summary(),
            'topological_order': self.get_topological_order(),
            'critical_path': self.get_critical_path(),
            'is_complete': self.is_complete()
        }
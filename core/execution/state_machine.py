from typing import Dict, Any, Optional, List
from models.task_models import TaskStatus, Task
from enum import Enum
from utils.logger import get_logger
from datetime import datetime


class GraphState(str, Enum):
    INITIALIZED = "initialized"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StateMachine:
    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        self.state = GraphState.INITIALIZED
        self.state_history: List[Dict[str, Any]] = []
        self.logger = get_logger(__name__)
        self.metadata: Dict[str, Any] = {}
        
        self._record_state_change(GraphState.INITIALIZED)
    
    def transition_to(self, new_state: GraphState, metadata: Optional[Dict[str, Any]] = None):
        valid_transitions = {
            GraphState.INITIALIZED: [GraphState.PLANNING, GraphState.CANCELLED],
            GraphState.PLANNING: [GraphState.EXECUTING, GraphState.FAILED, GraphState.CANCELLED],
            GraphState.EXECUTING: [GraphState.COMPLETED, GraphState.FAILED, GraphState.PAUSED, GraphState.CANCELLED],
            GraphState.PAUSED: [GraphState.EXECUTING, GraphState.CANCELLED],
            GraphState.COMPLETED: [],
            GraphState.FAILED: [GraphState.EXECUTING],
            GraphState.CANCELLED: []
        }
        
        if new_state not in valid_transitions.get(self.state, []):
            self.logger.warning(
                f"Invalid state transition: {self.state} -> {new_state}"
            )
            return False
        
        old_state = self.state
        self.state = new_state
        self._record_state_change(new_state, old_state, metadata)
        
        self.logger.info(f"State transition: {old_state} -> {new_state}")
        return True
    
    def _record_state_change(
        self,
        new_state: GraphState,
        old_state: Optional[GraphState] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'old_state': old_state.value if old_state else None,
            'new_state': new_state.value,
            'metadata': metadata or {}
        }
        self.state_history.append(record)
    
    def can_execute(self) -> bool:
        return self.state == GraphState.EXECUTING
    
    def is_terminal_state(self) -> bool:
        return self.state in [GraphState.COMPLETED, GraphState.FAILED, GraphState.CANCELLED]
    
    def get_current_state(self) -> GraphState:
        return self.state
    
    def get_state_history(self) -> List[Dict[str, Any]]:
        return self.state_history.copy()
    
    def set_metadata(self, key: str, value: Any):
        self.metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        return self.metadata.get(key)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'graph_id': self.graph_id,
            'current_state': self.state.value,
            'state_history': self.state_history,
            'metadata': self.metadata,
            'is_terminal': self.is_terminal_state()
        }
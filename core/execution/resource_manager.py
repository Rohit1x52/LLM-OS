from typing import Dict, Set, Optional, List
from datetime import datetime, timedelta
from utils.logger import get_logger
import asyncio


class ResourceManager:
    def __init__(self):
        self.resource_usage: Dict[str, int] = {}
        self.resource_limits: Dict[str, int] = {
            'api_calls': 100,
            'file_operations': 50,
            'database_connections': 10,
            'network_requests': 200,
            'cpu_intensive': 5
        }
        self.resource_windows: Dict[str, datetime] = {}
        self.window_duration = timedelta(minutes=1)
        self.locks: Set[str] = set()
        self.logger = get_logger("ResourceManager")

    async def acquire_resource(self, resource_type: str, count: int = 1) -> bool:
        self._reset_window_if_needed(resource_type)
        
        current_usage = self.resource_usage.get(resource_type, 0)
        limit = self.resource_limits.get(resource_type, float('inf'))
        
        if current_usage + count > limit:
            self.logger.warning(
                f"Resource limit reached for {resource_type}: "
                f"{current_usage}/{limit}"
            )
            return False
        
        self.resource_usage[resource_type] = current_usage + count
        self.logger.debug(f"Acquired {count} {resource_type} resource(s)")
        return True

    async def release_resource(self, resource_type: str, count: int = 1):
        current_usage = self.resource_usage.get(resource_type, 0)
        self.resource_usage[resource_type] = max(0, current_usage - count)
        self.logger.debug(f"Released {count} {resource_type} resource(s)")

    def _reset_window_if_needed(self, resource_type: str):
        now = datetime.utcnow()
        last_reset = self.resource_windows.get(resource_type)
        
        if not last_reset or (now - last_reset) > self.window_duration:
            self.resource_usage[resource_type] = 0
            self.resource_windows[resource_type] = now
            self.logger.debug(f"Reset resource window for {resource_type}")

    async def wait_for_resource(self, resource_type: str, count: int = 1, timeout: float = 30.0):
        start_time = datetime.utcnow()
        
        while True:
            if await self.acquire_resource(resource_type, count):
                return True
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= timeout:
                self.logger.error(f"Timeout waiting for {resource_type} resource")
                return False
            
            await asyncio.sleep(0.5)

    async def acquire_lock(self, lock_id: str, timeout: float = 10.0) -> bool:
        start_time = datetime.utcnow()
        
        while lock_id in self.locks:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= timeout:
                self.logger.warning(f"Timeout acquiring lock: {lock_id}")
                return False
            await asyncio.sleep(0.1)
        
        self.locks.add(lock_id)
        self.logger.debug(f"Acquired lock: {lock_id}")
        return True

    async def release_lock(self, lock_id: str):
        if lock_id in self.locks:
            self.locks.remove(lock_id)
            self.logger.debug(f"Released lock: {lock_id}")

    def get_resource_usage(self) -> Dict[str, Dict[str, int]]:
        return {
            resource: {
                'current': self.resource_usage.get(resource, 0),
                'limit': limit
            }
            for resource, limit in self.resource_limits.items()
        }

    def set_resource_limit(self, resource_type: str, limit: int):
        self.resource_limits[resource_type] = limit
        self.logger.info(f"Set resource limit for {resource_type}: {limit}")

    def check_conflicts(self, tasks: List[str]) -> List[tuple]:
        conflicts = []
        
        for i, task1 in enumerate(tasks):
            for task2 in tasks[i+1:]:
                if self._tasks_conflict(task1, task2):
                    conflicts.append((task1, task2))
        
        return conflicts

    def _tasks_conflict(self, task1: str, task2: str) -> bool:
        return False
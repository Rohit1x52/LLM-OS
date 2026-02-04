from typing import Callable, Any, Optional, Awaitable
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState
)
import asyncio
from utils.logger import get_logger
from datetime import datetime


class RetryHandler:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.logger = get_logger(__name__)
    
    def create_retry_decorator(
        self,
        task_id: str,
        retry_exceptions: tuple = (Exception,)
    ):
        def before_sleep(retry_state: RetryCallState):
            attempt = retry_state.attempt_number
            exception = retry_state.outcome.exception() if retry_state.outcome else None
            
            self.logger.warning(
                f"Task {task_id} failed (attempt {attempt}/{self.max_retries}). "
                f"Error: {exception}. Retrying in {retry_state.next_action.sleep} seconds..."
            )
        
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self.base_delay,
                min=self.base_delay,
                max=self.max_delay
            ),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep,
            reraise=True
        )
    
    async def execute_with_retry(
        self,
        task_id: str,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Any:
        retry_decorator = self.create_retry_decorator(task_id)
        
        @retry_decorator
        async def wrapped():
            return await func(*args, **kwargs)
        
        try:
            result = await wrapped()
            return result
        except Exception as e:
            self.logger.error(f"Task {task_id} failed after {self.max_retries} retries: {e}")
            raise
    
    def calculate_backoff(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        if attempt >= self.max_retries:
            return False
        
        non_retryable_exceptions = (
            ValueError,
            TypeError,
            KeyError,
        )
        
        if isinstance(exception, non_retryable_exceptions):
            self.logger.info(f"Non-retryable exception: {type(exception).__name__}")
            return False
        
        return True
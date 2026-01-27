from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from utils.logger import get_logger
from config.settings import settings


class ContextWindow:
    def __init__(self, max_size: int = 4000):
        self.max_size = max_size
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.logger = get_logger(__name__)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self._trim_if_needed()
    
    def _trim_if_needed(self):
        total_size = sum(len(msg["content"]) for msg in self.messages)
        
        while total_size > self.max_size and len(self.messages) > 1:
            removed = self.messages.pop(0)
            total_size -= len(removed["content"])
            self.logger.info(f"Trimmed message from context window")
    
    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages.copy()
    
    def clear(self):
        self.messages.clear()
        self.metadata.clear()
    
    def get_context_string(self) -> str:
        return "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in self.messages
        ])
    
    def set_metadata(self, key: str, value: Any):
        self.metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        return self.metadata.get(key)


class ContextManager:
    def __init__(self):
        self.context_window = ContextWindow(max_size=settings.context_window_size)
        self.session_data: Dict[str, Any] = {}
        self.logger = get_logger(__name__)
    
    def add_user_message(self, content: str, metadata: Optional[Dict] = None):
        self.context_window.add_message("user", content, metadata)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None):
        self.context_window.add_message("assistant", content, metadata)
    
    def add_system_message(self, content: str, metadata: Optional[Dict] = None):
        self.context_window.add_message("system", content, metadata)
    
    def get_context(self) -> List[Dict[str, Any]]:
        return self.context_window.get_messages()
    
    def get_context_string(self) -> str:
        return self.context_window.get_context_string()
    
    def clear_context(self):
        self.context_window.clear()
        self.logger.info("Context cleared")
    
    def enrich_context(self, key: str, value: Any):
        self.session_data[key] = value
        self.context_window.set_metadata(key, value)
    
    def get_enrichment(self, key: str) -> Optional[Any]:
        return self.session_data.get(key)
    
    def get_recent_messages(self, n: int = 5) -> List[Dict[str, Any]]:
        messages = self.context_window.get_messages()
        return messages[-n:] if len(messages) >= n else messages
    
    def get_token_count_estimate(self) -> int:
        context_str = self.get_context_string()
        return len(context_str.split())
    
    def export_context(self) -> str:
        context_data = {
            "messages": self.context_window.get_messages(),
            "session_data": self.session_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return json.dumps(context_data, indent=2)
    
    def import_context(self, context_json: str):
        try:
            context_data = json.loads(context_json)
            self.context_window.messages = context_data.get("messages", [])
            self.session_data = context_data.get("session_data", {})
            self.logger.info("Context imported successfully")
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to import context: {e}")
            raise
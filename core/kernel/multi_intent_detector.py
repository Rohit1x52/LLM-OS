from typing import Dict, List, Any, Optional
from utils.logger import get_logger
import re


class SubIntent:
    def __init__(
        self,
        action: str,
        entities: Dict[str, Any],
        sequence_position: int,
        dependencies: List[int] = None
    ):
        self.action = action
        self.entities = entities
        self.sequence_position = sequence_position
        self.dependencies = dependencies or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action,
            'entities': self.entities,
            'sequence_position': self.sequence_position,
            'dependencies': self.dependencies
        }


class MultiIntentDetector:
    def __init__(self):
        self.logger = get_logger(__name__)
        
        self.conjunction_patterns = [
            r'\band\b',
            r'\bthen\b',
            r'\balso\b',
            r'\bafter that\b',
            r'\bnext\b',
            r'\bfinally\b',
            r'\bplus\b',
            r'\badditionally\b'
        ]
        
        self.sequential_markers = [
            'first', 'second', 'third', 'then', 'next', 'after', 'finally', 'lastly'
        ]
    
    def detect(self, text: str) -> Dict[str, Any]:
        self.logger.info(f"Detecting multiple intents in: {text}")
        
        has_multiple = self._has_multiple_intents(text)
        
        if not has_multiple:
            return {
                'is_compound': False,
                'intent_count': 1,
                'sub_intents': [],
                'execution_order': 'single'
            }
        
        segments = self._segment_text(text)
        sub_intents = self._extract_sub_intents(segments)
        execution_order = self._determine_execution_order(text, segments)
        dependencies = self._build_dependency_graph(sub_intents, text)
        
        for idx, intent in enumerate(sub_intents):
            intent.dependencies = dependencies.get(idx, [])
        
        return {
            'is_compound': True,
            'intent_count': len(sub_intents),
            'sub_intents': [intent.to_dict() for intent in sub_intents],
            'execution_order': execution_order,
            'segments': segments
        }
    
    def _has_multiple_intents(self, text: str) -> bool:
        for pattern in self.conjunction_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        action_verbs = [
            'send', 'create', 'schedule', 'download', 'upload',
            'write', 'read', 'delete', 'update', 'search',
            'analyze', 'compile', 'execute', 'notify'
        ]
        
        verb_count = sum(1 for verb in action_verbs if verb in text.lower())
        return verb_count >= 2
    
    def _segment_text(self, text: str) -> List[str]:
        segments = []
        
        combined_pattern = '|'.join(self.conjunction_patterns)
        parts = re.split(f'({combined_pattern})', text, flags=re.IGNORECASE)
        
        current_segment = ""
        for part in parts:
            part = part.strip()
            if re.match(combined_pattern, part, re.IGNORECASE):
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = ""
            else:
                current_segment += " " + part
        
        if current_segment.strip():
            segments.append(current_segment.strip())
        
        if len(segments) <= 1:
            segments = [s.strip() for s in text.split(',') if s.strip()]
        
        return segments if len(segments) > 1 else [text]
    
    def _extract_sub_intents(self, segments: List[str]) -> List[SubIntent]:
        sub_intents = []
        
        for idx, segment in enumerate(segments):
            action = self._extract_action_from_segment(segment)
            entities = self._extract_entities_from_segment(segment)
            
            sub_intent = SubIntent(
                action=action,
                entities=entities,
                sequence_position=idx
            )
            sub_intents.append(sub_intent)
        
        return sub_intents
    
    def _extract_action_from_segment(self, segment: str) -> str:
        action_verbs = [
            'send', 'email', 'create', 'make', 'schedule', 'book',
            'download', 'fetch', 'upload', 'write', 'read', 'open',
            'delete', 'remove', 'update', 'modify', 'search', 'find',
            'analyze', 'process', 'compile', 'build', 'execute', 'run'
        ]
        
        words = segment.lower().split()
        for word in words:
            cleaned = re.sub(r'[^\w]', '', word)
            if cleaned in action_verbs:
                return cleaned
        
        return 'unknown'
    
    def _extract_entities_from_segment(self, segment: str) -> Dict[str, Any]:
        entities = {}
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, segment)
        if emails:
            entities['email'] = emails[0]
        
        file_pattern = r'\b[\w\-]+\.(pdf|doc|docx|txt|csv|xlsx|jpg|png)\b'
        files = re.findall(file_pattern, segment.lower())
        if files:
            entities['file'] = f"{files[0][0]}.{files[0][1]}"
        
        time_pattern = r'\b\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?\b'
        times = re.findall(time_pattern, segment)
        if times:
            entities['time'] = times[0]
        
        return entities
    
    def _determine_execution_order(
        self,
        text: str,
        segments: List[str]
    ) -> str:
        text_lower = text.lower()
        
        has_sequential = any(marker in text_lower for marker in self.sequential_markers)
        
        if has_sequential or 'then' in text_lower or 'after' in text_lower:
            return 'sequential'
        
        if 'parallel' in text_lower or 'simultaneously' in text_lower:
            return 'parallel'
        
        dependency_words = ['with', 'using', 'from', 'based on']
        has_dependencies = any(word in text_lower for word in dependency_words)
        
        if has_dependencies:
            return 'sequential'
        
        return 'sequential'
    
    def _build_dependency_graph(
        self,
        sub_intents: List[SubIntent],
        original_text: str
    ) -> Dict[int, List[int]]:
        
        dependencies = {}
        text_lower = original_text.lower()
        
        for idx, intent in enumerate(sub_intents):
            if idx == 0:
                dependencies[idx] = []
                continue
            
            intent_deps = []
            
            if 'with' in text_lower or 'using' in text_lower:
                if intent.action in ['send', 'email', 'share']:
                    if any(prev.action in ['create', 'write', 'summarize'] 
                           for prev in sub_intents[:idx]):
                        intent_deps.append(idx - 1)
            
            if not intent_deps:
                intent_deps.append(idx - 1)
            
            dependencies[idx] = intent_deps
        
        return dependencies
    
    def can_parallelize(self, detection_result: Dict[str, Any]) -> bool:
        if not detection_result['is_compound']:
            return False
        
        if detection_result['execution_order'] == 'parallel':
            return True
        
        sub_intents = detection_result['sub_intents']
        for intent in sub_intents:
            if intent.get('dependencies'):
                return False
        
        return True
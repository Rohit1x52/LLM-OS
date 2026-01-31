from typing import Dict, List, Any, Optional
from core.model.intent_model import IntentModel
from core.kernel.action_taxonomy import ActionTaxonomy, ActionCategory
from utils.logger import get_logger
import re


class Intent:
    def __init__(
        self,
        action: str,
        category: Optional[ActionCategory],
        entities: Dict[str, Any],
        confidence: float,
        raw_text: str
    ):
        self.action = action
        self.category = category
        self.entities = entities
        self.confidence = confidence
        self.raw_text = raw_text
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "category": self.category.value if self.category else None,
            "entities": self.entities,
            "confidence": self.confidence,
            "raw_text": self.raw_text
        }


class IntentParser:
    def __init__(self):
        self.intent_model = IntentModel()
        self.action_taxonomy = ActionTaxonomy()
        self.logger = get_logger(__name__)
    
    def parse(self, text: str) -> Intent:
        self.logger.info(f"Parsing intent from: {text}")
        
        action_verb = self._extract_action_verb(text)
        category = self.action_taxonomy.get_category(action_verb) if action_verb else None
        
        model_prediction = self.intent_model.predict(text)
        
        entities = self._extract_basic_entities(text)
        
        intent = Intent(
            action=action_verb or model_prediction['primary_intent'],
            category=category,
            entities=entities,
            confidence=model_prediction['confidence'],
            raw_text=text
        )
        
        self.logger.info(f"Parsed intent: {intent.to_dict()}")
        return intent
    
    def _extract_action_verb(self, text: str) -> Optional[str]:
        words = text.lower().split()
        all_verbs = self.action_taxonomy.get_all_action_verbs()
        
        for word in words[:5]:
            cleaned_word = re.sub(r'[^\w\s]', '', word)
            if cleaned_word in all_verbs:
                return cleaned_word
        
        return None
    
    def _extract_basic_entities(self, text: str) -> Dict[str, Any]:
        entities = {}
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            entities['emails'] = emails
        
        file_pattern = r'\b[\w\-]+\.(pdf|doc|docx|txt|csv|xlsx|jpg|png|json|xml)\b'
        files = re.findall(file_pattern, text.lower())
        if files:
            entities['files'] = [f"{name}.{ext}" for name, ext in files]
        
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        if urls:
            entities['urls'] = urls
        
        return entities
    
    def parse_batch(self, texts: List[str]) -> List[Intent]:
        return [self.parse(text) for text in texts]
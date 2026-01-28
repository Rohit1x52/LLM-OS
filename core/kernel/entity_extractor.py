from typing import Dict, List, Any, Set
import spacy
from spacy.tokens import Doc
import re
from datetime import datetime, timedelta
from utils.logger import get_logger
from config.settings import settings


class Entity:
    def __init__(self, text: str, label: str, start: int, end: int):
        self.text = text
        self.label = label
        self.start = start
        self.end = end
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "label": self.label,
            "start": self.start,
            "end": self.end
        }


class EntityExtractor:
    def __init__(self):
        self.logger = get_logger(__name__)
        try:
            self.nlp = spacy.load(settings.spacy_model)
            self.logger.info(f"Loaded spaCy model: {settings.spacy_model}")
        except OSError:
            self.logger.warning(f"Model {settings.spacy_model} not found, using en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
        
        self.custom_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, str]:
        return {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'url': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            'file_path': r'(?:[a-zA-Z]:\\|/)(?:[^\\/:*?"<>|\r\n]+[\\\/])*[^\\/:*?"<>|\r\n]*',
            'file_name': r'\b[\w\-]+\.(pdf|doc|docx|txt|csv|xlsx|xls|jpg|jpeg|png|gif|json|xml|yaml|py|js|html|css)\b',
            'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'time': r'\b\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?\b',
        }
    
    def extract(self, text: str) -> Dict[str, List[Entity]]:
        doc = self.nlp(text)
        
        entities: Dict[str, List[Entity]] = {
            'PERSON': [],
            'ORG': [],
            'GPE': [],
            'DATE': [],
            'TIME': [],
            'MONEY': [],
            'EMAIL': [],
            'PHONE': [],
            'URL': [],
            'FILE': [],
            'CUSTOM': []
        }
        
        for ent in doc.ents:
            label = ent.label_
            if label in entities:
                entities[label].append(
                    Entity(ent.text, label, ent.start_char, ent.end_char)
                )
        
        self._extract_custom_entities(text, entities)
        
        return entities
    
    def _extract_custom_entities(self, text: str, entities: Dict[str, List[Entity]]):
        for pattern_name, pattern in self.custom_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start, end = match.span()
                entity_text = match.group()
                
                if pattern_name == 'email':
                    entities['EMAIL'].append(
                        Entity(entity_text, 'EMAIL', start, end)
                    )
                elif pattern_name == 'phone':
                    entities['PHONE'].append(
                        Entity(entity_text, 'PHONE', start, end)
                    )
                elif pattern_name == 'url':
                    entities['URL'].append(
                        Entity(entity_text, 'URL', start, end)
                    )
                elif pattern_name in ['file_path', 'file_name']:
                    entities['FILE'].append(
                        Entity(entity_text, 'FILE', start, end)
                    )
                else:
                    entities['CUSTOM'].append(
                        Entity(entity_text, pattern_name.upper(), start, end)
                    )
    
    def extract_temporal(self, text: str) -> Dict[str, Any]:
        doc = self.nlp(text)
        temporal_info = {
            'dates': [],
            'times': [],
            'durations': [],
            'relative_dates': []
        }
        
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                temporal_info['dates'].append(ent.text)
            elif ent.label_ == 'TIME':
                temporal_info['times'].append(ent.text)
        
        relative_date_patterns = [
            r'\b(today|tomorrow|yesterday)\b',
            r'\bnext\s+(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\blast\s+(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\bin\s+(\d+)\s+(day|week|month|year)s?\b'
        ]
        
        for pattern in relative_date_patterns:
            matches = re.findall(pattern, text.lower())
            temporal_info['relative_dates'].extend(matches)
        
        return temporal_info
    
    def get_entities_by_type(self, text: str, entity_type: str) -> List[Entity]:
        entities = self.extract(text)
        return entities.get(entity_type.upper(), [])
    
    def get_all_entities_flat(self, text: str) -> List[Entity]:
        entities = self.extract(text)
        flat_list = []
        for entity_list in entities.values():
            flat_list.extend(entity_list)
        return sorted(flat_list, key=lambda e: e.start)
    
    def extract_key_phrases(self, text: str) -> List[str]:
        doc = self.nlp(text)
        phrases = []
        
        for chunk in doc.noun_chunks:
            phrases.append(chunk.text)
        
        return phrases
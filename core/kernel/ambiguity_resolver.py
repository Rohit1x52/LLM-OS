from typing import Dict, List, Any, Optional, Tuple
from utils.logger import get_logger
import re


class AmbiguityType:
    PRONOUN_REFERENCE = "pronoun_reference"
    INCOMPLETE_INFO = "incomplete_info"
    MULTIPLE_INTERPRETATIONS = "multiple_interpretations"
    TEMPORAL_AMBIGUITY = "temporal_ambiguity"
    ENTITY_AMBIGUITY = "entity_ambiguity"


class AmbiguityResolver:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.pronoun_references = ['it', 'this', 'that', 'these', 'those', 'them', 'they']
        self.temporal_vague = ['soon', 'later', 'sometime', 'eventually']
    
    def detect_ambiguities(
        self,
        text: str,
        entities: Dict[str, List[Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        
        ambiguities = []
        
        pronoun_ambiguity = self._check_pronoun_ambiguity(text, context)
        if pronoun_ambiguity:
            ambiguities.append(pronoun_ambiguity)
        
        incomplete_info = self._check_incomplete_information(text, entities)
        if incomplete_info:
            ambiguities.append(incomplete_info)
        
        temporal_ambiguity = self._check_temporal_ambiguity(text, entities)
        if temporal_ambiguity:
            ambiguities.append(temporal_ambiguity)
        
        entity_ambiguity = self._check_entity_ambiguity(entities)
        if entity_ambiguity:
            ambiguities.append(entity_ambiguity)
        
        return ambiguities
    
    def _check_pronoun_ambiguity(
        self,
        text: str,
        context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        
        words = text.lower().split()
        found_pronouns = [word for word in words if word in self.pronoun_references]
        
        if found_pronouns and not context:
            return {
                'type': AmbiguityType.PRONOUN_REFERENCE,
                'severity': 'high',
                'description': f"Pronouns found ({', '.join(found_pronouns)}) without clear reference",
                'suggestion': "Please specify what you're referring to",
                'pronouns': found_pronouns
            }
        
        return None
    
    def _check_incomplete_information(
        self,
        text: str,
        entities: Dict[str, List[Any]]
    ) -> Optional[Dict[str, Any]]:
        
        action_verbs = ['send', 'create', 'schedule', 'download', 'upload', 'email']
        has_action = any(verb in text.lower() for verb in action_verbs)
        
        if not has_action:
            return None
        
        missing_components = []
        
        if 'send' in text.lower() or 'email' in text.lower():
            if not entities.get('EMAIL') and not entities.get('PERSON'):
                missing_components.append('recipient')
        
        if 'schedule' in text.lower():
            if not entities.get('DATE') and not entities.get('TIME'):
                missing_components.append('time/date')
        
        if 'create' in text.lower() or 'write' in text.lower():
            if not entities.get('FILE'):
                missing_components.append('output destination')
        
        if missing_components:
            return {
                'type': AmbiguityType.INCOMPLETE_INFO,
                'severity': 'medium',
                'description': f"Missing information: {', '.join(missing_components)}",
                'suggestion': f"Please provide {', '.join(missing_components)}",
                'missing': missing_components
            }
        
        return None
    
    def _check_temporal_ambiguity(
        self,
        text: str,
        entities: Dict[str, List[Any]]
    ) -> Optional[Dict[str, Any]]:
        
        text_lower = text.lower()
        vague_terms = [term for term in self.temporal_vague if term in text_lower]
        
        if vague_terms:
            return {
                'type': AmbiguityType.TEMPORAL_AMBIGUITY,
                'severity': 'low',
                'description': f"Vague time references: {', '.join(vague_terms)}",
                'suggestion': "Consider specifying exact dates/times",
                'vague_terms': vague_terms
            }
        
        return None
    
    def _check_entity_ambiguity(
        self,
        entities: Dict[str, List[Any]]
    ) -> Optional[Dict[str, Any]]:
        
        persons = entities.get('PERSON', [])
        if len(persons) > 3:
            return {
                'type': AmbiguityType.ENTITY_AMBIGUITY,
                'severity': 'medium',
                'description': f"Multiple people mentioned ({len(persons)})",
                'suggestion': "Clarify which person is the primary contact",
                'entity_count': len(persons)
            }
        
        return None
    
    def resolve_with_context(
        self,
        text: str,
        ambiguities: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        
        resolved_text = text
        remaining_ambiguities = []
        
        for ambiguity in ambiguities:
            if ambiguity['type'] == AmbiguityType.PRONOUN_REFERENCE:
                resolved, success = self._resolve_pronouns(text, context)
                if success:
                    resolved_text = resolved
                else:
                    remaining_ambiguities.append(ambiguity)
            else:
                remaining_ambiguities.append(ambiguity)
        
        return resolved_text, remaining_ambiguities
    
    def _resolve_pronouns(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> Tuple[str, bool]:
        
        last_entity = context.get('last_mentioned_entity')
        last_file = context.get('last_file')
        
        if not last_entity and not last_file:
            return text, False
        
        resolved = text
        
        if 'it' in text.lower() and last_file:
            resolved = re.sub(r'\bit\b', last_file, resolved, flags=re.IGNORECASE, count=1)
            return resolved, True
        
        if 'this' in text.lower() and last_entity:
            resolved = re.sub(r'\bthis\b', last_entity, resolved, flags=re.IGNORECASE, count=1)
            return resolved, True
        
        return text, False
    
    def generate_clarification_questions(
        self,
        ambiguities: List[Dict[str, Any]]
    ) -> List[str]:
        
        questions = []
        
        for ambiguity in ambiguities:
            if ambiguity['type'] == AmbiguityType.PRONOUN_REFERENCE:
                questions.append("What specifically are you referring to?")
            
            elif ambiguity['type'] == AmbiguityType.INCOMPLETE_INFO:
                missing = ambiguity.get('missing', [])
                questions.append(f"Could you provide the {', '.join(missing)}?")
            
            elif ambiguity['type'] == AmbiguityType.TEMPORAL_AMBIGUITY:
                questions.append("When exactly would you like this to happen?")
            
            elif ambiguity['type'] == AmbiguityType.ENTITY_AMBIGUITY:
                questions.append("Which person should I focus on?")
        
        return questions
    
    def get_severity_score(self, ambiguities: List[Dict[str, Any]]) -> float:
        if not ambiguities:
            return 0.0
        
        severity_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
        scores = [severity_map.get(amb.get('severity', 'low'), 0.5) for amb in ambiguities]
        
        return sum(scores) / len(scores)
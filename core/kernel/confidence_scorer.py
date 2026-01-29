from typing import Dict, List, Any, Optional
import numpy as np
from utils.logger import get_logger
from config.settings import settings


class ConfidenceScorer:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.threshold = settings.confidence_threshold
        
        self.weights = {
            'intent_confidence': 0.35,
            'entity_completeness': 0.25,
            'clarity_score': 0.20,
            'context_alignment': 0.20
        }
    
    def calculate_confidence(
        self,
        intent_confidence: float,
        entities: Dict[str, List[Any]],
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        
        entity_score = self._calculate_entity_completeness(entities)
        clarity_score = self._calculate_clarity_score(text)
        context_score = self._calculate_context_alignment(text, context)
        
        overall_confidence = (
            self.weights['intent_confidence'] * intent_confidence +
            self.weights['entity_completeness'] * entity_score +
            self.weights['clarity_score'] * clarity_score +
            self.weights['context_alignment'] * context_score
        )
        
        needs_clarification = overall_confidence < self.threshold
        
        result = {
            'overall_confidence': round(overall_confidence, 3),
            'intent_confidence': round(intent_confidence, 3),
            'entity_completeness': round(entity_score, 3),
            'clarity_score': round(clarity_score, 3),
            'context_alignment': round(context_score, 3),
            'needs_clarification': needs_clarification,
            'threshold': self.threshold
        }
        
        if needs_clarification:
            result['clarification_reasons'] = self._identify_clarification_needs(
                intent_confidence, entity_score, clarity_score, context_score
            )
        
        return result
    
    def _calculate_entity_completeness(self, entities: Dict[str, List[Any]]) -> float:
        total_entities = sum(len(ent_list) for ent_list in entities.values())
        
        if total_entities == 0:
            return 0.3
        
        important_entity_types = ['PERSON', 'EMAIL', 'FILE', 'DATE', 'ORG']
        important_count = sum(
            len(entities.get(ent_type, [])) 
            for ent_type in important_entity_types
        )
        
        if important_count > 0:
            completeness = min(important_count / 3.0, 1.0)
        else:
            completeness = min(total_entities / 5.0, 0.7)
        
        return completeness
    
    def _calculate_clarity_score(self, text: str) -> float:
        words = text.split()
        word_count = len(words)
        
        if word_count < 3:
            length_score = 0.3
        elif word_count < 6:
            length_score = 0.6
        elif word_count < 15:
            length_score = 1.0
        else:
            length_score = max(0.7, 1.0 - (word_count - 15) * 0.02)
        
        question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'which']
        has_question = any(word in text.lower() for word in question_words)
        
        ambiguous_words = ['maybe', 'probably', 'might', 'could', 'perhaps', 'something']
        ambiguity_count = sum(1 for word in ambiguous_words if word in text.lower())
        ambiguity_penalty = min(ambiguity_count * 0.15, 0.4)
        
        clarity = length_score - ambiguity_penalty
        
        if has_question and text.strip().endswith('?'):
            clarity *= 0.9
        
        return max(0.0, min(1.0, clarity))
    
    def _calculate_context_alignment(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]]
    ) -> float:
        if not context:
            return 0.5
        
        alignment_score = 0.5
        
        pronouns = ['it', 'this', 'that', 'these', 'those', 'them']
        has_pronoun = any(pronoun in text.lower().split() for pronoun in pronouns)
        
        if has_pronoun and context:
            alignment_score = 0.8
        elif not has_pronoun:
            alignment_score = 0.9
        
        return alignment_score
    
    def _identify_clarification_needs(
        self,
        intent_conf: float,
        entity_score: float,
        clarity_score: float,
        context_score: float
    ) -> List[str]:
        reasons = []
        
        if intent_conf < 0.6:
            reasons.append("Unclear intent - please rephrase what you want to do")
        
        if entity_score < 0.4:
            reasons.append("Missing key information - please provide more details")
        
        if clarity_score < 0.5:
            reasons.append("Request is ambiguous - please be more specific")
        
        if context_score < 0.4:
            reasons.append("Context unclear - what are you referring to?")
    
        return reasons

def should_ask_clarification(self, confidence_result: Dict[str, Any]) -> bool:
    return confidence_result['needs_clarification']

def get_clarification_prompt(self, confidence_result: Dict[str, Any]) -> str:
    if not confidence_result.get('needs_clarification'):
        return ""
    
    reasons = confidence_result.get('clarification_reasons', [])
    
    if len(reasons) == 1:
        return f"I need clarification: {reasons[0]}"
    else:
        return "I need clarification on the following:\n" + "\n".join(
            f"- {reason}" for reason in reasons
        )
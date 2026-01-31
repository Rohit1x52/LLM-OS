from typing import Dict, List, Tuple
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from utils.logger import get_logger
from config.settings import settings


class IntentModel:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.device = 0 if torch.cuda.is_available() else -1
        
        self.intent_labels = [
            "file_operation",
            "email_communication",
            "calendar_scheduling",
            "web_search",
            "data_analysis",
            "code_execution",
            "system_command",
            "information_query",
            "task_automation",
            "document_processing"
        ]
        
        try:
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=self.device
            )
            self.logger.info("Intent model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load intent model: {e}")
            raise
    
    def predict(self, text: str) -> Dict[str, any]:
        try:
            result = self.classifier(
                text,
                candidate_labels=self.intent_labels,
                multi_label=True
            )
            
            intent_scores = dict(zip(result['labels'], result['scores']))
            primary_intent = result['labels'][0]
            confidence = result['scores'][0]
            
            return {
                "primary_intent": primary_intent,
                "confidence": float(confidence),
                "all_intents": intent_scores
            }
        except Exception as e:
            self.logger.error(f"Intent prediction failed: {e}")
            return {
                "primary_intent": "unknown",
                "confidence": 0.0,
                "all_intents": {}
            }
    
    def predict_multiple(self, texts: List[str]) -> List[Dict[str, any]]:
        return [self.predict(text) for text in texts]
    
    def get_top_k_intents(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        result = self.predict(text)
        all_intents = result['all_intents']
        sorted_intents = sorted(all_intents.items(), key=lambda x: x[1], reverse=True)
        return sorted_intents[:k]
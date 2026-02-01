from core.kernel.intent_parser import IntentParser
from core.kernel.entity_extractor import EntityExtractor
from core.kernel.context_manager import ContextManager
from core.kernel.confidence_scorer import ConfidenceScorer
from core.kernel.ambiguity_resolver import AmbiguityResolver
from core.kernel.multi_intent_detector import MultiIntentDetector
from utils.logger import get_logger


class NLKernel:
    def __init__(self):
        self.intent_parser = IntentParser()
        self.entity_extractor = EntityExtractor()
        self.context_manager = ContextManager()
        self.confidence_scorer = ConfidenceScorer()
        self.ambiguity_resolver = AmbiguityResolver()
        self.multi_intent_detector = MultiIntentDetector()
        self.logger = get_logger(__name__)
    
    def process(self, user_input: str):
        self.logger.info(f"Processing input: {user_input}")
        
        self.context_manager.add_user_message(user_input)
        
        multi_intent_result = self.multi_intent_detector.detect(user_input)
        
        entities = self.entity_extractor.extract(user_input)
        entity_dict = {k: [e.to_dict() for e in v] for k, v in entities.items()}
        
        intent = self.intent_parser.parse(user_input)
        
        confidence_result = self.confidence_scorer.calculate_confidence(
            intent.confidence,
            entities,
            user_input,
            {'previous_messages': self.context_manager.get_recent_messages(3)}
        )
        
        ambiguities = self.ambiguity_resolver.detect_ambiguities(
            user_input,
            entities,
            self.context_manager.session_data
        )
        
        result = {
            'intent': intent.to_dict(),
            'entities': entity_dict,
            'confidence': confidence_result,
            'multi_intent': multi_intent_result,
            'ambiguities': ambiguities,
            'needs_clarification': confidence_result['needs_clarification'] or len(ambiguities) > 0
        }
        
        if result['needs_clarification']:
            clarification_msg = self._generate_clarification_message(
                confidence_result,
                ambiguities
            )
            result['clarification_message'] = clarification_msg
            self.logger.info(f"Clarification needed: {clarification_msg}")
        
        return result
    
    def _generate_clarification_message(self, confidence_result, ambiguities):
        messages = []
        
        if confidence_result.get('clarification_reasons'):
            messages.extend(confidence_result['clarification_reasons'])
        
        if ambiguities:
            amb_questions = self.ambiguity_resolver.generate_clarification_questions(ambiguities)
            messages.extend(amb_questions)
        
        if len(messages) == 1:
            return messages[0]
        else:
            return "I need clarification:\n" + "\n".join(f"- {msg}" for msg in messages)


def main():
    kernel = NLKernel()
    logger = get_logger(__name__)
    
    test_inputs = [
        "send email to john@example.com with summary of file.pdf and also schedule a follow-up meeting",
        "download the latest research papers and analyze them",
        "create a report and send it",
        "do something with that file"
    ]
    
    for test_input in test_inputs:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {test_input}")
        logger.info(f"{'='*80}")
        
        result = kernel.process(test_input)
        
        logger.info(f"\nIntent: {result['intent']['action']}")
        logger.info(f"Confidence: {result['confidence']['overall_confidence']:.2f}")
        logger.info(f"Compound: {result['multi_intent']['is_compound']}")
        
        if result['multi_intent']['is_compound']:
            logger.info(f"Sub-intents: {result['multi_intent']['intent_count']}")
            for sub in result['multi_intent']['sub_intents']:
                logger.info(f"  - {sub['action']}")
        
        if result['needs_clarification']:
            logger.info(f"\nClarification: {result['clarification_message']}")
        
        logger.info(f"\nEntities found:")
        for entity_type, entity_list in result['entities'].items():
            if entity_list:
                logger.info(f"  {entity_type}: {len(entity_list)} found")


if __name__ == "__main__":
    main()
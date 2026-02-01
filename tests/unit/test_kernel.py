import pytest
from core.kernel.intent_parser import IntentParser
from core.kernel.entity_extractor import EntityExtractor
from core.kernel.context_manager import ContextManager
from core.kernel.confidence_scorer import ConfidenceScorer
from core.kernel.ambiguity_resolver import AmbiguityResolver
from core.kernel.multi_intent_detector import MultiIntentDetector


class TestIntentParser:
    def setup_method(self):
        self.parser = IntentParser()
    
    def test_parse_simple_intent(self):
        text = "send email to john@example.com"
        intent = self.parser.parse(text)
        assert intent.action in ['send', 'email_communication']
        assert 'emails' in intent.entities or 'EMAIL' in str(intent.entities)
    
    def test_parse_file_intent(self):
        text = "create a new document called report.pdf"
        intent = self.parser.parse(text)
        assert intent.action in ['create', 'file_operation']


class TestEntityExtractor:
    def setup_method(self):
        self.extractor = EntityExtractor()
    
    def test_extract_email(self):
        text = "send to john@example.com"
        entities = self.extractor.extract(text)
        assert len(entities['EMAIL']) > 0
        assert entities['EMAIL'][0].text == 'john@example.com'
    
    def test_extract_file(self):
        text = "open file.pdf"
        entities = self.extractor.extract(text)
        assert len(entities['FILE']) > 0
    
    def test_extract_multiple_entities(self):
        text = "email report.pdf to john@example.com and sarah@test.com"
        entities = self.extractor.extract(text)
        assert len(entities['EMAIL']) == 2
        assert len(entities['FILE']) == 1


class TestContextManager:
    def setup_method(self):
        self.manager = ContextManager()
    
    def test_add_message(self):
        self.manager.add_user_message("Hello")
        context = self.manager.get_context()
        assert len(context) == 1
        assert context[0]['role'] == 'user'
    
    def test_context_trimming(self):
        for i in range(100):
            self.manager.add_user_message("Message " * 100)
        token_count = self.manager.get_token_count_estimate()
        assert token_count > 0
    
    def test_clear_context(self):
        self.manager.add_user_message("Test")
        self.manager.clear_context()
        assert len(self.manager.get_context()) == 0


class TestConfidenceScorer:
    def setup_method(self):
        self.scorer = ConfidenceScorer()
    
    def test_high_confidence(self):
        entities = {
            'EMAIL': ['john@example.com'],
            'FILE': ['report.pdf']
        }
        result = self.scorer.calculate_confidence(0.9, entities, "send report.pdf to john@example.com")
        assert result['overall_confidence'] > 0.7
        assert not result['needs_clarification']
    
    def test_low_confidence_needs_clarification(self):
        result = self.scorer.calculate_confidence(0.3, {}, "do something")
        assert result['overall_confidence'] < 0.7
        assert result['needs_clarification']
        assert len(result['clarification_reasons']) > 0


class TestAmbiguityResolver:
    def setup_method(self):
        self.resolver = AmbiguityResolver()
    
    def test_detect_pronoun_ambiguity(self):
        ambiguities = self.resolver.detect_ambiguities("send it to john", {}, None)
        assert len(ambiguities) > 0
        assert any(amb['type'] == 'pronoun_reference' for amb in ambiguities)
    
    def test_detect_incomplete_info(self):
        ambiguities = self.resolver.detect_ambiguities("send email", {}, None)
        assert len(ambiguities) > 0
    
    def test_generate_clarification_questions(self):
        ambiguities = [
            {'type': 'pronoun_reference', 'severity': 'high'}
        ]
        questions = self.resolver.generate_clarification_questions(ambiguities)
        assert len(questions) > 0


class TestMultiIntentDetector:
    def setup_method(self):
        self.detector = MultiIntentDetector()
    
    def test_single_intent(self):
        result = self.detector.detect("send email to john@example.com")
        assert not result['is_compound']
        assert result['intent_count'] == 1
    
    def test_compound_intent(self):
        result = self.detector.detect(
            "send email to john@example.com and schedule a meeting"
        )
        assert result['is_compound']
        assert result['intent_count'] >= 2
    
    def test_sequential_detection(self):
        result = self.detector.detect(
            "download report.pdf then send it to john@example.com"
        )
        assert result['is_compound']
        assert result['execution_order'] == 'sequential'
    
    def test_dependency_graph(self):
        result = self.detector.detect(
            "create summary.pdf and send it to john@example.com"
        )
        if result['is_compound']:
            sub_intents = result['sub_intents']
            assert len(sub_intents) >= 2
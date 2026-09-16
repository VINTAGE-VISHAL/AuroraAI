"""TrainingSerializer implementations for Phase C."""

from abc import ABC, abstractmethod
from typing import List, Optional

from aurora.interfaces.corpus import ITrainingSerializer
from aurora.models.training_corpus import (
    ChatMLMessage,
    ChatMLPayload,
    PlainTextPayload,
    SerializedCorpus,
    SerializedDocument,
    SerializedPayload,
    SerializedSample,
    TrainingCorpus,
    TrainingDocument,
    TrainingSample,
)


class ISerializationStrategy(ABC):
    """Strategy interface for compiling specific serialized payload formats."""

    @abstractmethod
    def serialize_payload(self, sample: TrainingSample) -> SerializedPayload:
        """Translates a TrainingSample into a specific SerializedPayload subclass."""
        pass


class PlainTextStrategy(ISerializationStrategy):
    """Strategy to serialize samples into standard pre-training plain text payloads."""

    def serialize_payload(self, sample: TrainingSample) -> PlainTextPayload:
        """Extracts the sample raw text directly."""
        return PlainTextPayload(text=sample.text)


class ChatMLStrategy(ISerializationStrategy):
    """Strategy to serialize samples into interactive conversational ChatML format."""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.system_prompt = system_prompt or "You are a helpful assistant reading trusted educational textbook material."

    def serialize_payload(self, sample: TrainingSample) -> ChatMLPayload:
        """Wraps the sample text in system, user, and assistant ChatML messages."""
        pages_str = ", ".join(map(str, sample.traceability.page_numbers)) if sample.traceability.page_numbers else "Unknown"
        messages = [
            ChatMLMessage(role="system", content=self.system_prompt),
            ChatMLMessage(
                role="user",
                content=(
                    f"Read the following segment from document '{sample.traceability.doc_id}' "
                    f"(Pages {pages_str}):"
                ),
            ),
            ChatMLMessage(role="assistant", content=sample.text),
        ]
        return ChatMLPayload(messages=messages)


class InstructionStrategy(ISerializationStrategy):
    """Strategy to expand structured segments into conversational instruction QA pairs."""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.system_prompt = system_prompt or "You are a helpful educational assistant grounded in database systems textbook material."

    @staticmethod
    def clean_educational_text(text: str) -> str:
        import re
        # Strip chapter labels (e.g. Chapter 8)
        text = re.sub(r'(?i)\b(?:C\s*H\s*A\s*P\s*T\s*E\s*R\s+\d+|Chapter\s+\d+|UNIT\s+[IVXLCDM]+)[:.\s-]*', '', text)
        # Strip section numbers (e.g. 15.6.4) at the start of paragraphs/lines
        text = re.sub(r'(?m)^\s*\d+(?:\.\d+)+[:.\s-]*', '', text)
        # Strip Figure, Table, and Exercise captions and their trailing lines
        text = re.sub(r'(?i)\b(?:Figure|Table|Exercise|Fig\.)\s+\d+(?:\.\d+)*\b[^\n]*', '', text)
        return text.strip()

    @staticmethod
    def is_valid_educational_sample(prompt: str, response: str, blueprint_name: str) -> bool:
        import re
        # Reject short/numeric OCR concept artifacts or short codes (e.g. Explain 344, Explain T1)
        concept_only = re.sub(r'(?i)\[.*?\]|What is|Explain|Differentiate|from an interview perspective|like I\'m learning|write a 16-mark answer on|Why do we use|Give short revision notes on|Give a real-world example of|and other database concepts|\?', '', prompt).strip()
        if len(concept_only) < 3 or concept_only.isdigit() or re.match(r'^[A-Za-z]\d+$', concept_only):
            return False

        # Filter 1: Discard if response length < 50 characters (unless flashcard)
        if len(response.strip()) < 50 and blueprint_name != "flashcard":
            return False
            
        # Filter 2: Discard if response contains table of contents / index leakage keywords
        garbage_keywords = [
            "subject index", "table of contents", "bibliography", 
            "exercises", "review questions", "references", "appendix",
            "page unknown", "document id:"
        ]
        lowered_resp = response.lower()
        lowered_prompt = prompt.lower()
        for kw in garbage_keywords:
            if kw in lowered_resp or kw in lowered_prompt:
                return False
                
        # Filter 3: Discard if response is just a copy of the heading or too short
        clean_resp = re.sub(r'### [^\n]+\n', '', response).strip()
        if not clean_resp or clean_resp.isdigit():
            return False
        if len(clean_resp) < 20:
            return False
            
        # Filter 4: Reject page numbers / OCR garbage (consisting solely of digits/junk)
        if re.match(r'^\d+$', clean_resp):
            return False

        # Filter 5: Require minimum educational content
        # Composed answer must contain at least one educational block header:
        if "### Core Definition" not in response and "### Explanation & Working Details" not in response and "### Practical Example" not in response:
            return False
            
        return True

    def serialize_payload(self, sample: TrainingSample) -> List[ChatMLPayload]:
        from aurora.corpus.dataset_generators import DeterministicQuestionGenerator, DeterministicAnswerReformatter
        from aurora.corpus.knowledge_extractor import KnowledgeExtractor
        from aurora.corpus.blueprints import KnowledgeComposer
        from aurora.models.training_corpus import ChatMLCitation
        
        q_gen = DeterministicQuestionGenerator()
        a_ref = DeterministicAnswerReformatter()
        extractor = KnowledgeExtractor()
        composer = KnowledgeComposer()
        
        heading_text = sample.metadata.heading_text or ""
        unit = extractor.extract(sample.text, heading_text, sample.sample_id)
        
        questions = q_gen.generate_questions(heading_text)
        
        citation = ChatMLCitation(
            source_document=sample.traceability.doc_id,
            chapter=DeterministicQuestionGenerator.clean_concept(heading_text) if heading_text else "General",
            heading=heading_text if heading_text else None,
            section=heading_text.split()[0] if (heading_text and heading_text.split() and heading_text.split()[0][0].isdigit()) else None,
            pages=sample.traceability.page_numbers,
            segment_ids=sample.traceability.source_segment_ids
        )
        
        payloads = []
        for level, q_text in questions:
            full_question = q_text
            blueprint_name = level.lower()
            
            # Map revision/interview prefixes
            if level == "Exam":
                full_question = f"[Exam Prep] {q_text}"
            elif level == "Interview":
                full_question = f"[Interview Prep] {q_text}"
            elif level == "Revision":
                full_question = f"[Quick Revision] {q_text}"
                
            formatted_answer = composer.compose(unit, blueprint_name)
            
            # Fallback if composer returned empty
            if not formatted_answer.strip():
                formatted_answer = a_ref.conversationalize(sample.text, heading_text)
                
            # Clean formatted response before verifying validity
            formatted_answer = self.clean_educational_text(formatted_answer)
            full_question = self.clean_educational_text(full_question)
            
            if not self.is_valid_educational_sample(full_question, formatted_answer, blueprint_name):
                continue
                
            messages = [
                ChatMLMessage(role="system", content=self.system_prompt),
                ChatMLMessage(role="user", content=full_question),
                ChatMLMessage(role="assistant", content=formatted_answer)
            ]
            payloads.append(ChatMLPayload(messages=messages, citation=citation))
            
        return payloads


class ExamStrategy(ISerializationStrategy):
    """Strategy to expand structured segments specifically for exam-oriented training."""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.system_prompt = system_prompt or "You are an expert tutor preparing a student for a database systems exam."

    def serialize_payload(self, sample: TrainingSample) -> List[ChatMLPayload]:
        from aurora.corpus.dataset_generators import DeterministicQuestionGenerator, DeterministicAnswerReformatter
        from aurora.corpus.knowledge_extractor import KnowledgeExtractor
        from aurora.corpus.blueprints import KnowledgeComposer
        from aurora.models.training_corpus import ChatMLCitation
        
        q_gen = DeterministicQuestionGenerator()
        a_ref = DeterministicAnswerReformatter()
        extractor = KnowledgeExtractor()
        composer = KnowledgeComposer()
        
        heading_text = sample.metadata.heading_text or ""
        unit = extractor.extract(sample.text, heading_text, sample.sample_id)
                    
        questions = [q for q in q_gen.generate_questions(heading_text) if q[0] == "Exam"]
        
        citation = ChatMLCitation(
            source_document=sample.traceability.doc_id,
            chapter=DeterministicQuestionGenerator.clean_concept(heading_text) if heading_text else "General",
            heading=heading_text if heading_text else None,
            section=heading_text.split()[0] if (heading_text and heading_text.split() and heading_text.split()[0][0].isdigit()) else None,
            pages=sample.traceability.page_numbers,
            segment_ids=sample.traceability.source_segment_ids
        )
        
        payloads = []
        for _, q_text in questions:
            formatted_answer = composer.compose(unit, "exam")
            if not formatted_answer.strip():
                formatted_answer = a_ref.conversationalize(sample.text, heading_text)
                
            formatted_answer = InstructionStrategy.clean_educational_text(formatted_answer)
            q_text_clean = InstructionStrategy.clean_educational_text(q_text)
            
            if not InstructionStrategy.is_valid_educational_sample(q_text_clean, formatted_answer, "exam"):
                continue
                
            messages = [
                ChatMLMessage(role="system", content=self.system_prompt),
                ChatMLMessage(role="user", content=f"[Exam Prep] {q_text_clean}"),
                ChatMLMessage(role="assistant", content=formatted_answer)
            ]
            payloads.append(ChatMLPayload(messages=messages, citation=citation))
            
        return payloads


class FlashcardStrategy(ISerializationStrategy):
    """Strategy to serialize segments into short concept lookup flashcards."""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.system_prompt = system_prompt or "You are a flashcard application helping students review database terms."

    def serialize_payload(self, sample: TrainingSample) -> List[ChatMLPayload]:
        from aurora.corpus.dataset_generators import DeterministicQuestionGenerator, DeterministicAnswerReformatter
        from aurora.corpus.knowledge_extractor import KnowledgeExtractor
        from aurora.corpus.blueprints import KnowledgeComposer
        from aurora.models.training_corpus import ChatMLCitation
        
        q_gen = DeterministicQuestionGenerator()
        a_ref = DeterministicAnswerReformatter()
        extractor = KnowledgeExtractor()
        composer = KnowledgeComposer()
        
        heading_text = sample.metadata.heading_text or ""
        unit = extractor.extract(sample.text, heading_text, sample.sample_id)
                    
        concept = q_gen.clean_concept(heading_text)
        
        citation = ChatMLCitation(
            source_document=sample.traceability.doc_id,
            chapter=concept,
            heading=heading_text if heading_text else None,
            section=heading_text.split()[0] if (heading_text and heading_text.split() and heading_text.split()[0][0].isdigit()) else None,
            pages=sample.traceability.page_numbers,
            segment_ids=sample.traceability.source_segment_ids
        )
        
        formatted_answer = composer.compose(unit, "flashcard")
        if not formatted_answer.strip():
            formatted_answer = a_ref.conversationalize(sample.text, heading_text)
            
        formatted_answer = InstructionStrategy.clean_educational_text(formatted_answer)
        concept_clean = InstructionStrategy.clean_educational_text(concept)
            
        if not InstructionStrategy.is_valid_educational_sample(f"Define the database concept: {concept_clean}", formatted_answer, "flashcard"):
            return []
            
        messages = [
            ChatMLMessage(role="system", content=self.system_prompt),
            ChatMLMessage(role="user", content=f"Define the database concept: {concept_clean}"),
            ChatMLMessage(role="assistant", content=formatted_answer)
        ]
        return [ChatMLPayload(messages=messages, citation=citation)]


class CorpusSerializer(ITrainingSerializer):
    """A serializer that delegates payload construction to a serialization strategy."""

    def __init__(self, strategy: ISerializationStrategy) -> None:
        self.strategy = strategy

    def serialize(self, corpus: TrainingCorpus) -> SerializedCorpus:
        """Transforms a TrainingCorpus into a SerializedCorpus using the configured strategy."""
        serialized_docs = [self._serialize_document(doc) for doc in corpus.documents]
        return SerializedCorpus(corpus_id=corpus.corpus_id, documents=serialized_docs)

    def _serialize_document(self, doc: TrainingDocument) -> SerializedDocument:
        """Serializes a single TrainingDocument supporting one-to-many sample expansion."""
        import hashlib
        serialized_samples = []
        for sample in doc.samples:
            payloads_or_payload = self.strategy.serialize_payload(sample)
            if isinstance(payloads_or_payload, list):
                for sub_idx, payload in enumerate(payloads_or_payload, start=1):
                    sample_id_input = f"{sample.sample_id}:{sub_idx}"
                    sample_id = hashlib.sha256(sample_id_input.encode("utf-8")).hexdigest()
                    serialized_samples.append(
                        SerializedSample(
                            sample_id=sample_id,
                            sequence_number=sample.sequence_number,
                            payload=payload,
                        )
                    )
            else:
                serialized_samples.append(
                    SerializedSample(
                        sample_id=sample.sample_id,
                        sequence_number=sample.sequence_number,
                        payload=payloads_or_payload,
                    )
                )
        return SerializedDocument(doc_id=doc.doc_id, samples=serialized_samples)

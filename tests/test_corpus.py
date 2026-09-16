"""Unit tests for Phase C - Lossless Training Corpus components."""

import json
from datetime import datetime, timezone
import uuid
import pytest

from aurora.config.settings import Settings
from aurora.core.exceptions import ConfigurationError, InterfaceError
from aurora.core.artifact import ArtifactMetadata, SourceReference
from aurora.corpus.builder import LosslessCorpusBuilder
from aurora.corpus.exporter import JSONLExporter
from aurora.corpus.pipeline import CorpusPipeline
from aurora.corpus.serializer import CorpusSerializer, PlainTextStrategy, ChatMLStrategy
from aurora.corpus.validator import CorpusValidator
from aurora.models.document import StructuredDocument, PipelineProvenance
from aurora.models.enums import DocumentState, SegmentType
from aurora.models.metadata import FileMetadata
from aurora.models.segment import DocumentSegment
from aurora.models import FrameworkInfo
from aurora.registry.module_registry import ModuleRegistry


@pytest.fixture
def sample_structured_document() -> StructuredDocument:
    """Fixture returning a mock StructuredDocument with segments."""
    doc_id = "math_textbook"
    prov = PipelineProvenance(
        stage=DocumentState.SEGMENTED,
        producer="Test",
        timestamp=datetime.now(timezone.utc),
        framework=FrameworkInfo(module_name="Test", module_version="0.1.0"),
    )
    
    segments = [
        DocumentSegment(
            segment_id="seg1",
            doc_id=doc_id,
            type=SegmentType.HEADING,
            text="# Introduction to Calculus",
            level=1,
            start_offset=0,
            end_offset=26,
            segment_index=0,
            provenance=prov,
            source_reference=SourceReference(source_uri="file://math.txt", page_number=1),
        ),
        DocumentSegment(
            segment_id="seg2",
            doc_id=doc_id,
            type=SegmentType.PARAGRAPH,
            text="Calculus is the mathematical study of continuous change.",
            level=0,
            start_offset=27,
            end_offset=83,
            segment_index=1,
            provenance=prov,
            source_reference=SourceReference(source_uri="file://math.txt", page_number=1),
        ),
    ]

    return StructuredDocument(
        doc_id=doc_id,
        segments=segments,
        metadata=FileMetadata(source_path="file://math.txt", file_type="txt", char_count=83),
        provenance=prov,
        artifact=ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            checksum="original_doc_hash",
            created_at=datetime.now(timezone.utc),
        ),
    )


def test_builder_and_validator_success(sample_structured_document: StructuredDocument) -> None:
    """Verify builder produces a valid TrainingCorpus and validator passes."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])
    
    # Check basic properties
    assert len(corpus.documents) == 1
    t_doc = corpus.documents[0]
    assert t_doc.doc_id == "math_textbook"
    assert len(t_doc.samples) == 1
    
    sample = t_doc.samples[0]
    assert sample.sequence_number == 1
    assert sample.traceability.heading_segment_id == "seg1"
    assert sample.traceability.source_segment_ids == ["seg1", "seg2"]
    assert sample.traceability.page_numbers == [1]
    assert sample.text == "# Introduction to CalculusCalculus is the mathematical study of continuous change."

    # Validation should pass successfully
    result = validator.validate(corpus)
    assert result.passed is True
    assert result.samples_checked == 1
    assert result.documents_checked == 1


def test_validator_fails_on_completeness(sample_structured_document: StructuredDocument) -> None:
    """Verify validator raises InterfaceError on empty text contents."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])

    # Alter text to empty to simulate content completeness failure
    object.__setattr__(corpus.documents[0].samples[0], "text", "  ")

    with pytest.raises(InterfaceError, match="Completeness"):
        validator.validate(corpus)


def test_validator_fails_on_ordering(sample_structured_document: StructuredDocument) -> None:
    """Verify validator raises InterfaceError when sample sequence has gaps."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])

    # Tamper sequence number to simulate sequence gap/ordering failure
    object.__setattr__(corpus.documents[0].samples[0], "sequence_number", 3)

    with pytest.raises(InterfaceError, match="Structural Integrity"):
        validator.validate(corpus)


def test_validator_fails_on_duplication(sample_structured_document: StructuredDocument) -> None:
    """Verify validator raises InterfaceError if duplicate segment IDs are mapped."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])

    # Duplicate trace ID inside segment list
    trace = corpus.documents[0].samples[0].traceability
    object.__setattr__(trace, "source_segment_ids", ["seg1", "seg1"])

    with pytest.raises(InterfaceError, match="Duplicate"):
        validator.validate(corpus)


def test_validator_fails_on_traceability(sample_structured_document: StructuredDocument) -> None:
    """Verify validator raises InterfaceError on unsorted page numbers."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])

    # Tamper page numbers to be unsorted
    trace = corpus.documents[0].samples[0].traceability
    object.__setattr__(trace, "page_numbers", [2, 1])

    with pytest.raises(InterfaceError, match="Traceability"):
        validator.validate(corpus)


def test_validator_fails_on_deterministic_ids(sample_structured_document: StructuredDocument) -> None:
    """Verify validator raises InterfaceError when sample ID is tampered with."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])

    # Tamper with sample ID
    object.__setattr__(corpus.documents[0].samples[0], "sample_id", "0" * 64)

    with pytest.raises(InterfaceError, match="Deterministic IDs"):
        validator.validate(corpus)


def test_validator_fails_on_metadata(sample_structured_document: StructuredDocument) -> None:
    """Verify validator raises InterfaceError on child_count mismatch."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])

    # Tamper with metadata
    meta = corpus.documents[0].samples[0].metadata
    object.__setattr__(meta, "child_count", 99)

    with pytest.raises(InterfaceError, match="Metadata"):
        validator.validate(corpus)


def test_validator_fails_on_structural_integrity(sample_structured_document: StructuredDocument) -> None:
    """Verify validator raises InterfaceError when sequence does not start at 1."""
    builder = LosslessCorpusBuilder()
    validator = CorpusValidator()

    corpus = builder.build([sample_structured_document])

    # Tamper with sequence number
    object.__setattr__(corpus.documents[0].samples[0], "sequence_number", 0)

    with pytest.raises(InterfaceError, match="Structural Integrity"):
        validator.validate(corpus)


def test_serializers(sample_structured_document: StructuredDocument) -> None:
    """Verify PlainText and ChatML serialization works as expected."""
    builder = LosslessCorpusBuilder()
    corpus = builder.build([sample_structured_document])

    plain_ser = CorpusSerializer(PlainTextStrategy())
    serialized_plain = plain_ser.serialize(corpus)
    assert len(serialized_plain.documents) == 1
    sample = serialized_plain.documents[0].samples[0]
    assert sample.payload.text == "# Introduction to CalculusCalculus is the mathematical study of continuous change."

    chatml_ser = CorpusSerializer(ChatMLStrategy(system_prompt="Custom System Prompt"))
    serialized_chatml = chatml_ser.serialize(corpus)
    assert len(serialized_chatml.documents) == 1
    messages = serialized_chatml.documents[0].samples[0].payload.messages
    assert messages[0].role == "system"
    assert messages[0].content == "Custom System Prompt"
    assert messages[1].role == "user"
    assert messages[2].role == "assistant"
    assert messages[2].content == "# Introduction to CalculusCalculus is the mathematical study of continuous change."


def test_exporter_writes_jsonl(tmp_path, sample_structured_document: StructuredDocument) -> None:
    """Verify JSONLExporter creates the correct jsonl file structure."""
    builder = LosslessCorpusBuilder()
    corpus = builder.build([sample_structured_document])

    plain_ser = CorpusSerializer(PlainTextStrategy())
    serialized_plain = plain_ser.serialize(corpus)

    exporter = JSONLExporter()
    out_file = tmp_path / "subdir" / "training.jsonl"
    result = exporter.export(serialized_plain, str(out_file))

    from datetime import timedelta
    from aurora.models import ExportFormat

    # Assert ExportResult correctness
    assert result.output_path == str(out_file)
    assert result.format == ExportFormat.JSONL
    assert result.documents_exported == 1
    assert result.samples_exported == 1
    assert result.bytes_written > 0
    assert result.checksum is not None
    assert result.export_duration >= timedelta(seconds=0.0)

    # Read back and verify lines
    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    parsed_first = json.loads(lines[0])
    assert parsed_first["payload"]["text"] == "# Introduction to CalculusCalculus is the mathematical study of continuous change."
    assert parsed_first["sample_id"] is not None


def test_pipeline_execution(tmp_path, sample_structured_document: StructuredDocument) -> None:
    """Verify end-to-end execution of the CorpusPipeline module via ModuleRegistry."""
    settings = Settings()
    out_file = tmp_path / "pipeline_training.jsonl"
    settings.corpus.output_path = str(out_file)
    settings.corpus.serializer_type = "chatml"

    # Lookup and run the component from the registry
    corpus_component_cls = ModuleRegistry.get("corpus")
    corpus_component = corpus_component_cls(settings)

    result = corpus_component.run([sample_structured_document])

    assert len(result.training_corpus.documents) == 1
    assert result.export_result.output_path == str(out_file)
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert "payload" in parsed
    assert "messages" in parsed["payload"]


def test_training_input_adapter(sample_structured_document: StructuredDocument, tmp_path) -> None:
    """Verify that the TrainingInputAdapter converts pipeline outputs correctly."""
    settings = Settings()
    out_file = tmp_path / "adapter_training.jsonl"
    settings.corpus.output_path = str(out_file)

    corpus_component = ModuleRegistry.get("corpus")(settings)
    pipeline_result = corpus_component.run([sample_structured_document])

    adapter = ModuleRegistry.get("training_input_adapter")(settings)
    training_input = adapter.run(pipeline_result)

    assert training_input.dataset_path == str(out_file)
    assert training_input.sample_count == 1
    assert training_input.checksum == pipeline_result.export_result.checksum
    from aurora.models import ExportFormat
    assert training_input.export_format == ExportFormat.JSONL
    assert training_input.config.model_name == "Qwen/Qwen3-8B"


def test_corpus_builder_truncation_split() -> None:
    """Verify that LosslessCorpusBuilder splits long text blocks into multiple samples to prevent truncation."""
    prov = PipelineProvenance(
        stage=DocumentState.SEGMENTED,
        producer="Test",
        timestamp=datetime.now(timezone.utc),
        framework=FrameworkInfo(module_name="Test", module_version="0.1.0"),
    )
    
    # Create 3 segments that are each 800 characters to exceed the 2000 character limit when combined
    segments = [
        DocumentSegment(
            segment_id="s1",
            doc_id="long_doc",
            type=SegmentType.PARAGRAPH,
            text="a" * 800,
            level=0,
            start_offset=0,
            end_offset=800,
            segment_index=0,
            provenance=prov,
        ),
        DocumentSegment(
            segment_id="s2",
            doc_id="long_doc",
            type=SegmentType.PARAGRAPH,
            text="b" * 800,
            level=0,
            start_offset=800,
            end_offset=1600,
            segment_index=1,
            provenance=prov,
        ),
        DocumentSegment(
            segment_id="s3",
            doc_id="long_doc",
            type=SegmentType.PARAGRAPH,
            text="c" * 800,
            level=0,
            start_offset=1600,
            end_offset=2400,
            segment_index=2,
            provenance=prov,
        ),
    ]

    doc_artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="doc_checksum",
        created_at=datetime.now(timezone.utc),
    )
    s_doc = StructuredDocument(
        doc_id="long_doc",
        segments=segments,
        metadata=FileMetadata(source_path="long_doc.txt", file_type="txt", char_count=2400),
        provenance=prov,
        artifact=doc_artifact,
    )

    builder = LosslessCorpusBuilder()
    corpus = builder.build([s_doc])

    # Should have split into 2 samples (800+800 = 1600 <= 2000, next makes it 2400 > 2000)
    assert len(corpus.documents[0].samples) == 2
    assert corpus.documents[0].samples[0].text == ("a" * 800 + "b" * 800)
    assert corpus.documents[0].samples[1].text == ("c" * 800)


def test_instruction_strategies_and_generators(sample_structured_document: StructuredDocument) -> None:
    """Verify that pluggable instruction, exam, and flashcard strategies generate correct conversational payloads."""
    from aurora.corpus.dataset_generators import DeterministicQuestionGenerator, DeterministicAnswerReformatter
    from aurora.corpus.serializer import InstructionStrategy, ExamStrategy, FlashcardStrategy

    # Test generators directly
    q_gen = DeterministicQuestionGenerator()
    a_ref = DeterministicAnswerReformatter()

    clean_chapter = q_gen.clean_concept("Chapter 21: Parallel and Distributed Storage")
    assert clean_chapter == "Parallel and Distributed Storage"

    clean_section = q_gen.clean_concept("21.3.1 Round-Robin")
    assert clean_section == "Round-Robin"

    questions = q_gen.generate_questions("21.3.1 Round-Robin")
    assert len(questions) == 10
    assert any(q[0] == "Beginner" and "Round-Robin" in q[1] for q in questions)
    assert any(q[0] == "Exam" and "Round-Robin" in q[1] for q in questions)

    # Test serializer strategy output
    builder = LosslessCorpusBuilder()
    corpus = builder.build([sample_structured_document])
    sample = corpus.documents[0].samples[0]

    # 1. InstructionStrategy
    inst_strat = InstructionStrategy()
    payloads = inst_strat.serialize_payload(sample)
    assert len(payloads) == 9
    assert payloads[0].citation is not None
    assert payloads[0].citation.source_document == "math_textbook"
    assert payloads[0].messages[0].role == "system"
    assert payloads[0].messages[1].role == "user"
    assert payloads[0].messages[2].role == "assistant"
    # Verify compiled educational blueprint layout headers
    assert "### Core Definition" in payloads[0].messages[2].content

    # 2. ExamStrategy
    exam_strat = ExamStrategy()
    exam_payloads = exam_strat.serialize_payload(sample)
    assert len(exam_payloads) == 1
    assert exam_payloads[0].messages[1].content.startswith("[Exam Prep]")

    # 3. FlashcardStrategy
    fc_strat = FlashcardStrategy()
    fc_payloads = fc_strat.serialize_payload(sample)
    assert len(fc_payloads) == 1
    assert "Define the database concept:" in fc_payloads[0].messages[1].content


def test_aekc_compiler_pipeline() -> None:
    """Verify that AEKC KnowledgeExtractor, BlueprintEngine, and KnowledgeComposer function correctly."""
    from aurora.corpus.knowledge_extractor import KnowledgeExtractor, BlockType
    from aurora.corpus.blueprints import BlueprintEngine, KnowledgeComposer

    extractor = KnowledgeExtractor()
    composer = KnowledgeComposer()

    text = "DBMS refers to a database management system. It consits of engines and schemas. For example, Oracle is a DBMS. The main advantage is efficiency."
    unit = extractor.extract(text, "Chapter 1: Intro to DBMS")

    assert unit.title == "Intro to DBMS"
    
    # Check block classification
    definitions = unit.get_blocks_of_type(BlockType.DEFINITION)
    assert len(definitions) > 0
    assert "refers to" in definitions[0].text

    advantages = unit.get_blocks_of_type(BlockType.ADVANTAGES)
    assert len(advantages) > 0
    assert "advantage" in advantages[0].text

    # Test composition
    composed_exam = composer.compose(unit, "exam")
    assert "### Core Definition" in composed_exam
    assert "### Advantages & Benefits" in composed_exam
    # Limitations are missing from text, so it must be cleanly omitted from layout
    assert "### Limitations & Drawbacks" not in composed_exam


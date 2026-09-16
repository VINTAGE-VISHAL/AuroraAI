"""Unit tests for contract validators."""

import pytest

from aurora.core.exceptions import InterfaceError
from aurora.models.concept import Concept
from aurora.models.curriculum import Curriculum
from aurora.models.dataset import InstructionDataset, QAPair
from aurora.models.document import RawDocument
from aurora.models.metadata import FileMetadata
from aurora.models.training import TrainingResult
from aurora.pipeline.pipeline import Pipeline
from aurora.validators.concept_validator import validate_concept
from aurora.validators.curriculum_validator import validate_curriculum
from aurora.validators.dataset_validator import validate_dataset
from aurora.validators.document_validator import validate_raw_document
from aurora.validators.metadata_validator import validate_metadata
from aurora.validators.pipeline_validator import validate_pipeline
from aurora.validators.training_validator import validate_training_result


def test_metadata_validation() -> None:
    valid_meta = FileMetadata(source_path="src/file.txt", file_type="txt", char_count=10)
    validate_metadata(valid_meta)  # Should not raise

    with pytest.raises(InterfaceError):
        invalid_meta = FileMetadata(source_path="src/file.txt", file_type="txt", char_count=-5)
        validate_metadata(invalid_meta)


def test_raw_document_validation() -> None:
    import uuid
    from datetime import datetime, timezone

    from aurora.models import ArtifactMetadata, FrameworkInfo, PipelineProvenance
    from aurora.models.enums import DocumentState

    valid_meta = FileMetadata(source_path="src/file.txt", file_type="txt", char_count=12)
    framework = FrameworkInfo(module_name="test", module_version="0.1")
    provenance = PipelineProvenance(
        stage=DocumentState.LOADED,
        producer="test",
        timestamp=datetime.now(timezone.utc),
        framework=framework,
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash123",
        created_at=provenance.timestamp,
    )
    valid_doc = RawDocument(
        doc_id="doc1",
        source_id="src1",
        uri="file:///src/file.txt",
        content_bytes=b"Hello World!",
        content_hash="hash123",
        state=DocumentState.LOADED,
        metadata=valid_meta,
        provenance=provenance,
        artifact=artifact,
    )
    validate_raw_document(valid_doc)

    with pytest.raises(InterfaceError):
        invalid_doc = RawDocument(
            doc_id="doc1",
            source_id="src1",
            uri="file:///src/file.txt",
            content_bytes=b"   ",
            content_hash="hash123",
            state=DocumentState.LOADED,
            metadata=valid_meta,
            provenance=provenance,
            artifact=artifact,
        )
        validate_raw_document(invalid_doc)



def test_concept_validation() -> None:
    valid_concept = Concept(
        name="AI Principles",
        description="Understanding systems.",
        difficulty="beginner",
        prerequisites=[],
        reference_chunk_ids=["chunk_1"],
    )
    validate_concept(valid_concept)

    with pytest.raises(InterfaceError):
        invalid_concept = Concept(
            name="AI Principles",
            description="Understanding systems.",
            difficulty="super-hard",  # invalid difficulty
            prerequisites=[],
            reference_chunk_ids=["chunk_1"],
        )
        validate_concept(invalid_concept)


def test_curriculum_validation() -> None:
    valid_concept = Concept(
        name="AI Principles",
        description="Understanding systems.",
        difficulty="beginner",
        prerequisites=[],
        reference_chunk_ids=["chunk_1"],
    )
    valid_curr = Curriculum(domain="AI", concepts=[valid_concept], version="1.0")
    validate_curriculum(valid_curr)

    with pytest.raises(InterfaceError):
        # Concept references invalid prerequisite
        invalid_concept = Concept(
            name="Advanced AI",
            description="Deep understanding.",
            difficulty="advanced",
            prerequisites=["NonExistentConcept"],
            reference_chunk_ids=["chunk_1"],
        )
        invalid_curr = Curriculum(domain="AI", concepts=[invalid_concept], version="1.0")
        validate_curriculum(invalid_curr)


def test_dataset_validation() -> None:
    valid_pair = QAPair(
        instruction="What is AI?", response="Artificial Intelligence.", reference_concept="AI"
    )
    valid_ds = InstructionDataset(name="AI Dataset", pairs=[valid_pair], split="train")
    validate_dataset(valid_ds)

    with pytest.raises(InterfaceError):
        invalid_pair = QAPair(
            instruction="", response="Artificial Intelligence.", reference_concept="AI"
        )
        invalid_ds = InstructionDataset(name="AI Dataset", pairs=[invalid_pair], split="train")
        validate_dataset(invalid_ds)


def test_training_result_validation() -> None:
    from datetime import timedelta
    from aurora.models import ComputeDType, EvaluationResult, TrainingConfig

    eval_res = EvaluationResult(
        loss=0.2,
        perplexity=1.2,
        evaluation_time=timedelta(seconds=5),
        passed=True,
    )

    t_config = TrainingConfig(
        model_name="Qwen/Qwen3-8B",
        tokenizer_name="Qwen/Qwen3-8B",
        dataset_path="/path/to/dataset.jsonl",
        output_dir="/path/to/output",
        epochs=3,
        batch_size=4,
        gradient_accumulation_steps=1,
        learning_rate=2e-4,
        warmup_ratio=0.03,
        weight_decay=0.01,
        max_seq_length=512,
        seed=42,
        lora_r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
        load_in_4bit=True,
        bnb_compute_dtype=ComputeDType.BFLOAT16,
        bf16=True,
        fp16=False,
        gradient_checkpointing=True,
        save_steps=100,
        logging_steps=10,
        eval_steps=100,
    )

    valid_res = TrainingResult(
        success=True,
        config=t_config,
        adapter_path="models/lora",
        tokenizer_path="models/tokenizer",
        checkpoints=[],
        evaluation=eval_res,
        training_time=timedelta(seconds=60),
        final_loss=0.1,
    )
    validate_training_result(valid_res)

    with pytest.raises(InterfaceError):
        invalid_res = TrainingResult(
            success=True,
            config=t_config,
            adapter_path="",  # empty adapter path for completed run
            tokenizer_path="models/tokenizer",
            checkpoints=[],
            evaluation=eval_res,
            training_time=timedelta(seconds=60),
            final_loss=0.1,
        )
        validate_training_result(invalid_res)


def test_pipeline_validation() -> None:
    valid_pipe = Pipeline([])
    with pytest.raises(InterfaceError):
        validate_pipeline(valid_pipe)

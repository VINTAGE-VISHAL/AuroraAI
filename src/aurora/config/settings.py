"""System settings configuration definitions."""

from aurora.config.base import BaseConfig


class IngestionConfig(BaseConfig):
    """Configuration settings for ingestion module."""
    raw_dir: str = "data/raw"


class PreprocessingConfig(BaseConfig):
    """Configuration settings for preprocessing module."""
    chunk_size: int = 500
    chunk_overlap: int = 50


class UnderstandingConfig(BaseConfig):
    """Configuration settings for knowledge extraction module."""
    model_name: str = "gpt-4"


class DatasetConfig(BaseConfig):
    """Configuration settings for QA and dataset engineering."""
    qa_pairs_per_chunk: int = 3


class TrainingConfig(BaseConfig):
    """Configuration settings for LoRA training."""
    lora_r: int = 8
    lora_alpha: int = 16
    epochs: int = 3
    learning_rate: float = 2e-5


class EvaluationConfig(BaseConfig):
    """Configuration settings for model evaluation."""
    metrics: list[str] = ["accuracy", "trustworthiness"]


class DeploymentConfig(BaseConfig):
    """Configuration settings for deployment."""
    port: int = 8000
    host: str = "0.0.0.0"


class CorpusConfig(BaseConfig):
    """Configuration settings for corpus module."""
    serializer_type: str = "chatml"  # "plain", "chatml", "instruction", "exam", or "flashcard"

    # Automatically isolate tests by default to prevent overwriting development data
    output_path: str = "data/corpus/training.jsonl"

    def __init__(self, **data):
        super().__init__(**data)
        import sys
        import os
        import tempfile
        if "pytest" in sys.modules and self.output_path == "data/corpus/training.jsonl":
            self.output_path = os.path.join(tempfile.gettempdir(), "aurora_test_training.jsonl")


class RuntimeStorageConfig(BaseConfig):
    """Configuration settings for runtime conversation-scoped file storage."""
    upload_dir: str = "data/runtime_uploads"
    max_upload_size_mb: int = 20
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt", ".md"]
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "application/octet-stream",  # Often sent by browsers for .md / generic text
    ]


class Settings(BaseConfig):
    """Unified application settings configuration."""
    project_name: str = "AuroraEngine"
    version: str = "0.1.0"

    ingestion: IngestionConfig = IngestionConfig()
    preprocessing: PreprocessingConfig = PreprocessingConfig()
    understanding: UnderstandingConfig = UnderstandingConfig()
    dataset: DatasetConfig = DatasetConfig()
    corpus: CorpusConfig = CorpusConfig()
    training: TrainingConfig = TrainingConfig()
    evaluation: EvaluationConfig = EvaluationConfig()
    deployment: DeploymentConfig = DeploymentConfig()
    runtime_storage: RuntimeStorageConfig = RuntimeStorageConfig()



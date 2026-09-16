"""Orchestrates Stage 1 QLoRA Training on Qwen3-8B-Instruct for Unified Multi-Subject Model (DBMS, DSA, OOPS, OS, CNT, OOSE)."""

import os
import sys
from datetime import datetime, timezone

# Resolve repository root dynamically
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts", "data_prep"))

from aurora.models import (
    ComputeDType,
    ExportFormat,
    ExportResult,
    TrainingConfig,
)
from aurora.evaluation import UnifiedSubjectEvaluator
from aurora.training.adapter import TrainingInputAdapter
from aurora.training.adapter_packager import AdapterPackager
from aurora.training.checkpoint_manager import CheckpointManager
from aurora.training.dataset_loader import DatasetLoader
from aurora.training.evaluator import Evaluator
from aurora.training.model_preparer import ModelPreparer
from aurora.training.pipeline import TrainingPipeline
from aurora.training.tokenizer_service import TokenizerService
from aurora.training.trainer import Trainer


def log_environment_details(config: TrainingConfig) -> None:
    """Logs the environment metadata at the start of the unified training run."""
    print("=" * 60)
    print("AURORA UNIFIED MULTI-SUBJECT TRAINING LOG")
    print("=" * 60)
    print(f"Timestamp:          {datetime.now(timezone.utc).isoformat()}")
    print(f"Aurora Version:     0.1.0")
    print(f"Model Repository:   {config.model_name}")
    print(f"Tokenizer Name:     {config.tokenizer_name}")
    print(f"Random Seed:        {config.seed}")
    print(f"Python Version:     {sys.version.split()[0]}")
    
    try:
        import torch
        print(f"PyTorch Version:    {torch.__version__}")
        print(f"CUDA Available:     {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU Name:           {torch.cuda.get_device_name(0)}")
            print(f"GPU Free Memory:    {torch.cuda.mem_get_info()[0] / (1024**3):.2f} GB")
            print(f"GPU Total Memory:   {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    except ImportError:
        print("PyTorch Version:    Not Installed")

    print(f"Dataset Path:       {config.dataset_path}")
    print(f"Output Directory:   {config.output_dir}")
    print(f"Max Seq Length:     {config.max_seq_length}")
    print(f"Quantization:       4-bit (Double Quantized)")
    print(f"LoRA Configuration: Rank={config.lora_r}, Alpha={config.lora_alpha}")
    print("=" * 60)


def main() -> None:
    corpus_file = os.path.join(REPO_ROOT, "data", "corpus", "unified_all_subjects_training.jsonl")
    output_dir = os.path.join(REPO_ROOT, "data", "output", "unified_adapter")
    
    # Auto-prepare unified corpus if missing
    if not os.path.exists(corpus_file):
        print("Unified corpus file not found. Triggering corpus builder...")
        import prepare_unified_corpus
        prepare_unified_corpus.main()

    config = TrainingConfig(
        model_name="Qwen/Qwen3-8B",
        tokenizer_name="Qwen/Qwen3-8B",
        dataset_path=corpus_file,
        output_dir=output_dir,
        epochs=1,
        batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=2e-4,
        warmup_ratio=0.03,
        weight_decay=0.01,
        max_seq_length=512,
        seed=42,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=[
            "q_proj",
            "v_proj",
        ],
        load_in_4bit=True,
        bnb_compute_dtype=ComputeDType.BFLOAT16,
        bf16=True,
        fp16=False,
        gradient_checkpointing=True,
        save_steps=500,
        logging_steps=10,
        eval_steps=500,
    )

    log_environment_details(config)

    # Initialize unified training pipeline components
    loader = DatasetLoader()
    tokenizer_service = TokenizerService()
    adapter = TrainingInputAdapter()
    preparer = ModelPreparer()
    trainer = Trainer()
    evaluator = UnifiedSubjectEvaluator()
    checkpoint_manager = CheckpointManager()
    packager = AdapterPackager()

    pipeline = TrainingPipeline(
        dataset_loader=loader,
        tokenizer_service=tokenizer_service,
        training_adapter=adapter,
        model_preparer=preparer,
        trainer=trainer,
        evaluator=evaluator,
        checkpoint_manager=checkpoint_manager,
        adapter_packager=packager,
    )

    print("\nExecuting Unified Multi-Subject Training Pipeline...")
    final_output_path = pipeline.run(config)
    print(f"\nUnified Multi-Subject Adapter successfully created and packaged at:\n{final_output_path}")


if __name__ == "__main__":
    main()


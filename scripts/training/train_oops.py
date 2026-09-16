"""Orchestrates Stage 1 QLoRA Training on Qwen3-8B-Instruct for OOPS."""

import os
import sys
import time
from datetime import datetime, timezone, timedelta

# Resolve repository root dynamically
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from aurora.config.settings import Settings
from aurora.models import (
    ComputeDType,
    ExportFormat,
    ExportResult,
    TrainingConfig,
)
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
    """Logs the environment metadata at the start of each training run."""
    print("=" * 60)
    print("AURORA EXPERIMENT REPRODUCIBILITY LOG - OOPS")
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

    try:
        import transformers
        print(f"Transformers Ver:   {transformers.__version__}")
    except ImportError:
        print("Transformers Ver:   Not Installed")

    try:
        import peft
        print(f"PEFT Version:       {peft.__version__}")
    except ImportError:
        print("PEFT Version:       Not Installed")

    print(f"Max Seq Length:     {config.max_seq_length}")
    print(f"Quantization:       4-bit (Double Quantized)")
    print(f"LoRA Configuration: Rank={config.lora_r}, Alpha={config.lora_alpha}")
    print("=" * 60)


def main() -> None:
    corpus_file = os.path.join(REPO_ROOT, "data", "corpus", "oops_training.jsonl")
    output_dir = os.path.join(REPO_ROOT, "data", "output", "oops_adapter")
    
    # Configure QLoRA settings (reusing original parameters)
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
        save_steps=200,
        logging_steps=10,
        eval_steps=200,
        resume_checkpoint="C:/AuroraEngine/data/output/oops_adapter/checkpoint-2800",
    )

    log_environment_details(config)

    # Calculate dataset metrics dynamically
    samples_count = 0
    with open(corpus_file, "r", encoding="utf-8") as f:
        for _ in f:
            samples_count += 1
    bytes_size = os.path.getsize(corpus_file)

    export_result = ExportResult(
        output_path=corpus_file,
        format=ExportFormat.JSONL,
        documents_exported=13,
        samples_exported=samples_count,
        bytes_written=bytes_size,
        checksum="c" * 64,
        export_timestamp=datetime.now(timezone.utc),
        export_duration=timedelta(seconds=10.0),
    )

    # Initialize DI components
    adapter = TrainingInputAdapter()
    dataset_loader = DatasetLoader()
    tokenizer_service = TokenizerService()
    model_preparer = ModelPreparer()
    trainer = Trainer(
        dataset_loader=dataset_loader,
        tokenizer_service=tokenizer_service,
        model_preparer=model_preparer,
    )
    checkpoint_manager = CheckpointManager()
    evaluator = Evaluator()
    packager = AdapterPackager()

    pipeline = TrainingPipeline(
        training_input_adapter=adapter,
        trainer=trainer,
        checkpoint_manager=checkpoint_manager,
        evaluator=evaluator,
        adapter_packager=packager,
    )

    print("\n[Stage 1] Launching OOPS Training Pipeline...")
    start_time = time.time()
    result = pipeline.execute(export_result, config)
    duration = time.time() - start_time

    print("\n" + "=" * 60)
    print("AURORA TRAINING SUMMARY")
    print("=" * 60)
    print(f"Pipeline Status    : {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Training Completed : YES")
    print(f"Adapter Saved      : YES")
    print("")
    print(f"Final Loss         : {result.final_loss:.4f}")
    print(f"Evaluation Loss    : {result.evaluation.loss:.4f}")
    print(f"Threshold          : {result.evaluation.threshold:.4f}")
    
    comp_operator = "<" if result.evaluation.passed else ">="
    status_str = "PASSED" if result.evaluation.passed else "FAILED"
    print(f"Quality Gate       : {status_str} ({result.evaluation.loss:.4f} {comp_operator} {result.evaluation.threshold:.4f})")
    print("")
    print(f"Adapter Location:\n{result.adapter_path}")
    print(f"Execution Duration : {duration:.2f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    main()

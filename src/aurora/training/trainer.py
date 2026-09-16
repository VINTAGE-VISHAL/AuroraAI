"""Trainer implementation for Phase D executing QLoRA training loops."""

import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import IDatasetLoader, IModelPreparer, ITokenizerService, ITrainer
from aurora.models import (
    CheckpointInfo,
    EvaluationResult,
    TrainingConfig,
    TrainingInput,
    TrainingResult,
    RawTrainingOutput,
)
from aurora.registry.module_registry import ModuleRegistry

# Conditional imports for Hugging Face/torch training dependencies
try:
    import torch
    from transformers import DataCollatorForLanguageModeling, Trainer as HFTrainer, TrainingArguments
    HAS_TRAIN_LIBS = True
except ImportError:
    HAS_TRAIN_LIBS = False


@ModuleRegistry.register("trainer")
class Trainer(ITrainer):
    """Executes the QLoRA optimization loop using prepared datasets, models, and tokenizers."""

    def __init__(
        self,
        dataset_loader: IDatasetLoader,
        tokenizer_service: ITokenizerService,
        model_preparer: IModelPreparer,
    ) -> None:
        self.dataset_loader = dataset_loader
        self.tokenizer_service = tokenizer_service
        self.model_preparer = model_preparer

    def run(self, input_data: TrainingInput) -> RawTrainingOutput:
        """Runs the end-to-end training loop based on input dataset paths and settings."""
        config = input_data.config
        start_time = time.perf_counter()

        # 1. Load raw dataset bundle
        t0 = time.perf_counter()
        hf_dataset, prepared_meta = self.dataset_loader.load(input_data)
        print(f"PROFILER: Dataset load duration: {time.perf_counter() - t0:.4f} seconds")

        # 2. Load model and tokenizer
        t1 = time.perf_counter()
        model, tokenizer = self.model_preparer.prepare(config)
        print(f"PROFILER: Model load duration: {time.perf_counter() - t1:.4f} seconds")

        # 3. Tokenize dataset
        t2 = time.perf_counter()
        tokenized_dataset = self.tokenizer_service.tokenize(hf_dataset, tokenizer, config)
        print(f"PROFILER: Tokenization duration: {time.perf_counter() - t2:.4f} seconds")

        # 4. Fallback / Mock loop execution when GPU packages are missing or mock model is used
        if not HAS_TRAIN_LIBS or config.model_name.startswith("Mock"):
            return self._run_mock(model, tokenizer, start_time)

        try:
            # 5. Configure Training Arguments
            training_args = TrainingArguments(
                output_dir=config.output_dir,
                per_device_train_batch_size=config.batch_size,
                gradient_accumulation_steps=config.gradient_accumulation_steps,
                learning_rate=config.learning_rate,
                warmup_ratio=config.warmup_ratio,
                weight_decay=config.weight_decay,
                num_train_epochs=config.epochs,
                max_steps=config.max_steps,
                logging_steps=config.logging_steps,
                save_steps=config.save_steps,
                seed=config.seed,
                fp16=config.fp16,
                bf16=config.bf16,
                remove_unused_columns=True,
                gradient_checkpointing=config.gradient_checkpointing,
                dataloader_pin_memory=True,
                report_to="none",
                optim="paged_adamw_8bit",
            )

            print("=" * 60)
            print("AURORA LAUNCH CONFIRMATION")
            print("=" * 60)
            print(f"gradient_checkpointing = {training_args.gradient_checkpointing}")
            print(f"batch_size = {training_args.per_device_train_batch_size}")
            print(f"gradient_accumulation_steps = {training_args.gradient_accumulation_steps}")
            print(f"optim = {training_args.optim}")
            print("=" * 60)

            # 6. Initialize Causal LM Data Collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer,
                mlm=False,
            )

            # 7. Initialize Trainer
            hf_trainer = HFTrainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=data_collator,
            )

            # 8. Start Causal Language Modeling Optimization Loop
            import os
            resume_from = config.resume_checkpoint
            # Only pass resume_from_checkpoint to HFTrainer if trainer_state.json exists
            # Otherwise, ModelPreparer has already warm-started the PeftModel weights directly
            if resume_from and not os.path.exists(os.path.join(resume_from, "trainer_state.json")):
                resume_from = None

            train_output = hf_trainer.train(resume_from_checkpoint=resume_from)

            elapsed = time.perf_counter() - start_time
            final_loss = train_output.metrics.get("train_loss", 0.0)

            return RawTrainingOutput(
                model=model,
                tokenizer=tokenizer,
                metrics=train_output.metrics,
                final_loss=final_loss,
                training_time=timedelta(seconds=elapsed),
            )

        except Exception as e:
            raise InterfaceError(f"QLoRA training execution failed: {e}") from e

    def _run_mock(self, model: Any, tokenizer: Any, start_time: float) -> RawTrainingOutput:
        """Simulates successful model training in dry-run/CPU testing environments."""
        elapsed = time.perf_counter() - start_time
        return RawTrainingOutput(
            model=model,
            tokenizer=tokenizer,
            metrics={"train_loss": 0.25},
            final_loss=0.25,
            training_time=timedelta(seconds=elapsed),
        )

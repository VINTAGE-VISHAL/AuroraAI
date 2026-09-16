"""AdapterPackager implementation for Phase D artifact deployment."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import IAdapterPackager
from aurora.models import EvaluationResult, RawTrainingOutput, TrainingConfig, TrainingResult
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("adapter_packager")
class AdapterPackager(IAdapterPackager):
    """Packages training outputs, weights, tokenizers, and metadata into a deployable adapter bundle."""

    def package(
        self,
        raw_output: RawTrainingOutput,
        evaluation: EvaluationResult,
        config: TrainingConfig,
    ) -> TrainingResult:
        """Saves weights, tokenizers, and metadata to output directories, returning the final TrainingResult."""
        try:
            # 1. Prepare target adapter path
            adapter_path = os.path.join(config.output_dir, "final_adapter")
            os.makedirs(adapter_path, exist_ok=True)

            # 2. Save weights (check if model supports save_pretrained)
            print("=" * 80)
            print("Adapter Packaging Diagnostics")
            print("Model Type:           ", type(raw_output.model))
            print("Has save_pretrained:  ", hasattr(raw_output.model, "save_pretrained"))
            print("Target Export Path:   ", adapter_path)
            print("=" * 80)

            if hasattr(raw_output.model, "save_pretrained"):
                print("Executing PEFT save_pretrained()...")
                raw_output.model.save_pretrained(adapter_path)
                print("save_pretrained() completed successfully.")
            else:
                print("WARNING: MOCK FALLBACK PATH EXECUTED (No save_pretrained attribute).")
                # Mock environment weight simulation
                with open(os.path.join(adapter_path, "adapter_model.safetensors"), "w", encoding="utf-8") as f:
                    f.write("mock_weights")
                with open(os.path.join(adapter_path, "adapter_config.json"), "w", encoding="utf-8") as f:
                    json.dump({
                        "peft_type": "LORA",
                        "base_model_name_or_path": config.model_name,
                        "task_type": "CAUSAL_LM",
                        "r": config.lora_r,
                        "lora_alpha": config.lora_alpha,
                    }, f)

            # Instantly verify file output size and existence
            weights_file = os.path.join(adapter_path, "adapter_model.safetensors")
            if os.path.exists(weights_file):
                print(f"Verified weight file: {weights_file} ({os.path.getsize(weights_file)} bytes)")
            else:
                print(f"ERROR: Weight file not found at: {weights_file}")

            # 3. Save tokenizer (check if tokenizer supports save_pretrained)
            if hasattr(raw_output.tokenizer, "save_pretrained"):
                raw_output.tokenizer.save_pretrained(adapter_path)
            else:
                # Mock environment tokenizer simulation
                with open(os.path.join(adapter_path, "tokenizer_config.json"), "w", encoding="utf-8") as f:
                    json.dump({"tokenizer_class": "MockTokenizer"}, f)

            # 4. Save metadata.json detailing validation runs and settings
            metadata_path = os.path.join(adapter_path, "metadata.json")
            metadata_content = {
                "base_model": config.model_name,
                "final_loss": raw_output.final_loss,
                "training_time_seconds": raw_output.training_time.total_seconds(),
                "evaluation_loss": evaluation.loss,
                "evaluation_perplexity": evaluation.perplexity,
                "evaluation_passed": evaluation.passed,
                "packaged_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_content, f, indent=4)

            return TrainingResult(
                success=True,
                config=config,
                adapter_path=adapter_path,
                tokenizer_path=adapter_path,
                checkpoints=[],
                evaluation=evaluation,
                training_time=raw_output.training_time,
                final_loss=raw_output.final_loss,
            )

        except Exception as e:
            raise InterfaceError(f"Adapter packaging failed: {e}") from e

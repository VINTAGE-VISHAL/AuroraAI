"""ModelPreparer implementation for Phase D."""

import sys
from typing import Any, Tuple, Union

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import IModelPreparer
from aurora.models import ComputeDType, TrainingConfig
from aurora.training.mocks import MockModelObj, MockTokenizerObj

# Conditional imports for Hugging Face PEFT/transformers dependencies
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from transformers import PreTrainedModel, PreTrainedTokenizerBase
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    HAS_HF_LIBS = True
except ImportError:
    # Fail-safe fallbacks for type checking when packages are absent
    class PreTrainedModel:  # type: ignore[no-redef]
        pass

    class PreTrainedTokenizerBase:  # type: ignore[no-redef]
        pass
    HAS_HF_LIBS = False

# Type unions to eliminate 'Any' while accommodating mock/test implementations
PreparedModel = Union[PreTrainedModel, MockModelObj]
PreparedTokenizer = Union[PreTrainedTokenizerBase, MockTokenizerObj]


class ModelPreparer(IModelPreparer):
    """Loads and configures base models with PEFT LoRA adapter injections."""

    def prepare(self, config: TrainingConfig) -> Tuple[PreparedModel, PreparedTokenizer]:
        """Loads and prepares the model and tokenizer for QLoRA fine-tuning."""
        # 1. Fallback / Mock Mode for testing or dry-runs without GPU/HuggingFace dependencies
        if config.model_name.startswith("Mock") or not HAS_HF_LIBS:
            return MockModelObj(config), MockTokenizerObj()

        try:
            # 2. Map compute data types
            torch_dtype = self._map_compute_dtype(config.bnb_compute_dtype)

            # 3. Configure quantization
            bnb_config = None
            if config.load_in_4bit:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type=config.quant_type,
                    bnb_4bit_compute_dtype=torch_dtype,
                    bnb_4bit_use_double_quant=True,
                )

            # 4. Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                config.tokenizer_name,
                trust_remote_code=config.trust_remote_code,
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # 5. Load base model
            model = AutoModelForCausalLM.from_pretrained(
                config.model_name,
                quantization_config=bnb_config,
                device_map=config.device_map,
                trust_remote_code=config.trust_remote_code,
                torch_dtype=torch_dtype,
                attn_implementation="sdpa",
            )
            model.config.use_cache = False

            # 6. Prepare model for kbit/quantized training (enabling gradient checkpointing internally)
            model = prepare_model_for_kbit_training(
                model,
                use_gradient_checkpointing=config.gradient_checkpointing,
            )

            # 7. Configure and inject LoRA adapters (or load existing pre-trained adapter for warm-start)
            import os
            if config.resume_checkpoint and os.path.exists(os.path.join(config.resume_checkpoint, "adapter_config.json")):
                from peft import PeftModel
                print(f"Warm-starting QLoRA continuation training from pre-trained adapter: '{config.resume_checkpoint}'...")
                model = PeftModel.from_pretrained(
                    model,
                    config.resume_checkpoint,
                    is_trainable=True,
                )
            else:
                peft_config = LoraConfig(
                    r=config.lora_r,
                    lora_alpha=config.lora_alpha,
                    target_modules=config.target_modules,
                    lora_dropout=config.lora_dropout,
                    bias="none",
                    task_type="CAUSAL_LM",
                )
                model = get_peft_model(model, peft_config)
            
            # Print trainable parameters to console as a QLoRA sanity check
            try:
                model.print_trainable_parameters()
            except Exception:
                pass

            return model, tokenizer

        except Exception as e:
            raise InterfaceError(f"Model preparation failed: {e}") from e

    def _map_compute_dtype(self, bnb_compute_dtype: ComputeDType) -> Any:
        """Translates compute dtype configurations to torch constants."""
        if bnb_compute_dtype == ComputeDType.FLOAT16:
            return torch.float16
        elif bnb_compute_dtype == ComputeDType.BFLOAT16:
            return torch.bfloat16
        else:
            return torch.float32

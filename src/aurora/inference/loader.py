"""ModelLoader implementation utilizing singleton model caching."""

import threading
from typing import Any, Tuple

from aurora.core.exceptions import InterfaceError
from aurora.inference.interfaces import IModelLoader
from aurora.registry.module_registry import ModuleRegistry
from aurora.training.mocks import MockModelObj, MockTokenizerObj

# Conditional imports for PyTorch/Transformers
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HAS_HF_LIBS = True
except ImportError:
    HAS_HF_LIBS = False


@ModuleRegistry.register("model_loader")
class ModelLoader(IModelLoader):
    """Thread-safe Singleton caching base causal models and tokenizers in VRAM/RAM."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelLoader, cls).__new__(cls)
                cls._instance._model = None
                cls._instance._tokenizer = None
                cls._instance._loaded_name = None
                cls._instance._load_time = 0.0
            return cls._instance

    def load(self, model_name: str, trust_remote_code: bool = False) -> Tuple[Any, Any]:
        """Loads model_name once. Subsequent calls retrieve the cached instance."""
        with self._lock:
            if self._model is not None and self._loaded_name == model_name:
                return self._model, self._tokenizer

            # Mock fallbacks for testing or CPU environments without packages
            if model_name.startswith("Mock") or not HAS_HF_LIBS:
                from aurora.models import TrainingConfig, ComputeDType
                # Create a mini dummy config for MockModelObj
                dummy_config = TrainingConfig(
                    model_name=model_name,
                    tokenizer_name=model_name,
                    dataset_path="mock.jsonl",
                    output_dir="output",
                    epochs=1,
                    batch_size=1,
                    gradient_accumulation_steps=1,
                    learning_rate=2e-5,
                    warmup_ratio=0.0,
                    weight_decay=0.01,
                    max_seq_length=512,
                    seed=42,
                    lora_r=8,
                    lora_alpha=16,
                    lora_dropout=0.05,
                    target_modules=["q_proj"],
                    load_in_4bit=True,
                    bnb_compute_dtype=ComputeDType.FLOAT16,
                    bf16=False,
                    fp16=True,
                    gradient_checkpointing=False,
                    save_steps=10,
                    logging_steps=1,
                    eval_steps=10,
                )
                self._model = MockModelObj(dummy_config)
                self._tokenizer = MockTokenizerObj()
                self._loaded_name = model_name
                return self._model, self._tokenizer

            try:
                import time
                t_start = time.perf_counter()
                # Resolve computation precision and hardware speedups
                dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
                device = "cuda:0" if torch.cuda.is_available() else None

                if torch.cuda.is_available():
                    torch.backends.cuda.matmul.allow_tf32 = True
                    torch.backends.cudnn.allow_tf32 = True
                    try:
                        torch.set_float32_matmul_precision("high")
                    except Exception:
                        pass

                print(f"Loading base model '{model_name}' (device_map={device}, dtype={dtype})...")
                self._tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    trust_remote_code=trust_remote_code,
                )
                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token

                # Configure quantization config (matching training QLoRA configuration)
                bnb_config = None
                attn_impl = "sdpa" if torch.cuda.is_available() else "eager"
                if torch.cuda.is_available():
                    from transformers import BitsAndBytesConfig
                    bnb_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=dtype,
                        bnb_4bit_use_double_quant=True,
                    )

                self._model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=bnb_config,
                    device_map=device,
                    torch_dtype=dtype,
                    attn_implementation=attn_impl,
                    trust_remote_code=trust_remote_code,
                )
                self._loaded_name = model_name
                self._load_time = time.perf_counter() - t_start
                print(f"Successfully loaded and cached '{model_name}' in memory in {self._load_time:.3f}s.")
                return self._model, self._tokenizer
            except Exception as e:
                raise InterfaceError(f"ModelLoader failed to load base model: {e}") from e

    def get_loaded(self) -> Tuple[Any, Any]:
        """Gets currently loaded cache or raises InterfaceError."""
        with self._lock:
            if self._model is None:
                raise InterfaceError("No model has been loaded yet. Call load() first.")
            return self._model, self._tokenizer

    def get_load_time(self) -> float:
        """Gets the loading time of the base model in seconds."""
        with self._lock:
            return self._load_time

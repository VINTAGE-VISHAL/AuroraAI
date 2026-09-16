"""AdapterManager implementation for dynamic LoRA switching."""

from typing import Any
from aurora.core.exceptions import InterfaceError
from aurora.inference.interfaces import IAdapterManager
from aurora.registry.module_registry import ModuleRegistry

# Conditional PEFT import
try:
    from peft import PeftModel
    HAS_PEFT = True
except ImportError:
    HAS_PEFT = False


@ModuleRegistry.register("adapter_manager")
class AdapterManager(IAdapterManager):
    """Manages active LoRA adapters wrapped around cached base models."""

    def __init__(self) -> None:
        self._current_adapter_path = ""
        self._peft_wrapped = False

    def set_adapter(self, model: Any, adapter_path: str, adapter_name: str = "default") -> Any:
        """Loads and switches to a specific adapter. Wraps the model in PeftModel if needed."""
        if not adapter_path:
            return self.unload_adapter(model)

        # Mock Mode
        if not HAS_PEFT or hasattr(model, "is_mock") or type(model).__name__ == "MockModelObj":
            model.active_adapter = adapter_path
            self._current_adapter_path = adapter_path
            return model

        try:
            import torch
            if torch.cuda.is_available():
                target_device = "cuda:0"
                torch.cuda.empty_cache()
            else:
                target_device = "cpu"

            # If model is already a PeftModel, load or activate the target adapter
            if isinstance(model, PeftModel):
                if adapter_path in model.peft_config:
                    model.set_adapter(adapter_name)
                else:
                    model.load_adapter(adapter_path, adapter_name, torch_device=target_device)
                    model.set_adapter(adapter_name)
                peft_model = model
            else:
                # Wrap base model in PeftModel for the first time
                print(f"Wrapping model with PEFT adapter from '{adapter_path}' (target_device={target_device})...")
                peft_model = PeftModel.from_pretrained(
                    model,
                    adapter_path,
                    adapter_name=adapter_name,
                    is_trainable=False,
                    autocast_adapter_dtype=False,
                )
                if torch.cuda.is_available():
                    # Move all newly mounted LoRA linear parameters to GPU
                    for name, param in peft_model.named_parameters():
                        if "lora_" in name and param.device.type == "cpu":
                            param.data = param.data.to(target_device)
                try:
                    # Print device diagnostic check
                    print("Base device:", next(peft_model.get_base_model().parameters()).device)
                    print("PEFT device:", next(peft_model.parameters()).device)
                except Exception as e:
                    print(f"Diagnostics error: {e}")
                self._peft_wrapped = True

            # Scale adapter down dynamically to prevent loop repetitions
            # and allow native Qwen3 reasoning to control conversation structure.
            for name, module in peft_model.named_modules():
                if hasattr(module, "scaling") and isinstance(module.scaling, dict):
                    module.scaling[adapter_name] = 0.4

            self._current_adapter_path = adapter_path
            return peft_model

        except Exception as e:
            raise InterfaceError(f"AdapterManager failed to load adapter '{adapter_path}': {e}") from e

    def unload_adapter(self, model: Any) -> Any:
        """Detaches adapters to return model to its raw base state without merging weights."""
        if hasattr(model, "active_adapter"):
            delattr(model, "active_adapter")
        self._current_adapter_path = ""
        return model

    def get_current_adapter(self) -> str:
        """Gets active adapter identifier path."""
        return self._current_adapter_path

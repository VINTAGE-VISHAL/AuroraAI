"""Model preparation utilities loading base weights and injecting adapter strategies."""

from aurora.training.interfaces import ModelPrepContext


class ModelPreparer:
    """Utility managing model loading and PEFT strategy configurations."""

    def prepare(self, context: ModelPrepContext) -> ModelPrepContext:
        """Injects adapter config layers into the base model weight structures."""
        # Mock loading base model
        model_name = context.config.base_model_id
        strategy = context.config.adapter_strategy.value

        mock_model = {
            "model_name": model_name,
            "adapter_injected": True,
            "strategy": strategy,
            "lora_r": context.config.lora_r,
            "lora_alpha": context.config.lora_alpha,
            "parameter_count": 1000000,
            "trainable_parameter_count": 50000,
        }

        object.__setattr__(context, "model", mock_model)
        return context

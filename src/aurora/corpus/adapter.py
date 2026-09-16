"""Adapter component connecting Phase C outputs to Phase D inputs."""

from aurora.config.settings import Settings
from aurora.interfaces.base import IPipelineComponent
from aurora.models.training_corpus import CorpusPipelineResult
from aurora.models.training import TrainingInput
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("training_input_adapter")
class TrainingInputAdapter(IPipelineComponent[CorpusPipelineResult, TrainingInput]):
    """Pipeline component adapting CorpusPipelineResult to TrainingInput."""

    def __init__(self, config: Settings) -> None:
        self.config = config

    def run(self, input_data: CorpusPipelineResult) -> TrainingInput:
        """Adapts CorpusPipelineResult to the new QLoRA TrainingInput structure."""
        from aurora.models import ComputeDType, TrainingConfig
        from aurora.training.adapter import TrainingInputAdapter as PhaseDAdapter

        # Construct a default QLoRA TrainingConfig using settings/defaults
        t_config = TrainingConfig(
            model_name="Qwen/Qwen3-8B",
            tokenizer_name="Qwen/Qwen3-8B",
            dataset_path=input_data.export_result.output_path,
            output_dir="models/lora_adapter",
            epochs=self.config.training.epochs,
            batch_size=4,
            gradient_accumulation_steps=1,
            learning_rate=self.config.training.learning_rate,
            warmup_ratio=0.03,
            weight_decay=0.01,
            max_seq_length=512,
            seed=42,
            lora_r=self.config.training.lora_r,
            lora_alpha=self.config.training.lora_alpha,
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

        phase_d_adapter = PhaseDAdapter()
        return phase_d_adapter.adapt(input_data.export_result, t_config)

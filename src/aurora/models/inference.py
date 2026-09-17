"""Data models for inference and evaluation lab sessions."""

from pydantic import BaseModel, ConfigDict, Field


class GenerationResult(BaseModel):
    """Immutable model representing the outcome of a text generation prompt."""
    model_config = ConfigDict(frozen=True)

    answer: str
    generation_time: float = Field(description="Execution time in seconds")
    tokens_generated: int = Field(description="Number of newly generated tokens")
    tokens_per_second: float = Field(description="Generation speed throughput")

    base_load_time: float = Field(default=0.0, description="Base model initial load time")
    adapter_load_time: float = Field(default=0.0, description="LoRA adapter loading time")
    specialist_gen_time: float = Field(default=0.0, description="Stage 1 specialist generation duration")
    specialist_tokens: int = Field(default=0, description="Stage 1 generated token count")
    specialist_tps: float = Field(default=0.0, description="Stage 1 tokens per second speed")
    adapter_unload_time: float = Field(default=0.0, description="LoRA adapter unloading/detaching duration")
    vanilla_gen_time: float = Field(default=0.0, description="Stage 2 Vanilla Qwen generation duration")
    vanilla_tokens: int = Field(default=0, description="Stage 2 generated token count")
    vanilla_tps: float = Field(default=0.0, description="Stage 2 tokens per second speed")

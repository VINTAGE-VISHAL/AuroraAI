"""Enums for model precision, optimization types, scheduling, and run states."""

from enum import Enum


class Precision(Enum):
    """Supported floating-point training precision states."""
    FP16 = "fp16"
    BF16 = "bf16"
    FP32 = "fp32"


class OptimizerType(Enum):
    """Supported backpropagation optimization strategies."""
    ADAMW = "adamw_torch"
    PAGED_ADAMW_8BIT = "paged_adamw_8bit"
    SGD = "sgd"


class SchedulerType(Enum):
    """Supported learning rate decay decay schedules."""
    COSINE = "cosine"
    LINEAR = "linear"
    CONSTANT = "constant"


class AdapterStrategy(Enum):
    """Supported adapter injection strategies."""
    LORA = "lora"
    QLORA = "qlora"
    FULL = "full"


class TrainingRunStatus(Enum):
    """State indicators of training execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

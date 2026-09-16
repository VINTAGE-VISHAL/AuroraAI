# ADR 0012: Training Provenance and Reproducibility

## Context
Aurora Platform trains educational language models (adapters) using Dataset Studio releases. To make training runs fully reproducible, trackable, and explainable, we require strict tracking of hyperparameters, optimizer settings, dataset inputs, environment dependencies, and evaluation checkpoints. Coupling the trainer execution to a single library (e.g. Hugging Face PEFT) will limit future adaptations (e.g. custom PyTorch loops or other parameter-efficient techniques).

## Decision
We implement a pluggable, environment-aware **Training Engine** based on these invariants:
1. **Experiment Lineage**: Every `TrainingRun` records base model revisions, environment snapshots, and links dataset releases to the produced `AdapterDescriptor`.
2. **Pluggable Backends**: Training executors implement the `ITrainingBackend` interface, allowing backends to be swapped out (e.g., Mock training backend, Hugging Face Trainer backend, or custom PyTorch training backend).
3. **Configuration Strong Typing**: Hyperparameters, optimizers, and precision states are governed by explicit enums (`Precision`, `OptimizerType`, `SchedulerType`, `AdapterStrategy`).
4. **Environment Snapshots**: Every run takes an snapshot of dependency libraries (e.g. `torch`, `transformers`, `peft`) and hardware parameters to avoid replication errors.
5. **Layered Evaluation**: Models are evaluated on standard loss/perplexity, instruction accuracy, and educational metrics (concept coverage, prerequisite preservation, and groundedness).

## Consequences
- Deep lineage tracking: downstream inference pipelines can trace any model response back to the training hyperparameters, dataset collections, and exact source Knowledge Units.
- Extensibility: new adapters or model scaling methods can be tested without breaking the training orchestrator pipeline.

## Base Model Selection
We standardize the initial training configuration on the following model options:
- **Base Model Identifier**: `Qwen/Qwen2.5-7B-Instruct` (7.2B parameter scale) or `Qwen/Qwen1.5-8B-Chat` (8B parameter scale)
- **License**: Apache License 2.0 (permitting commercial usage, modifications, and redistribution)
- **Reasoning**: Strong multi-lingual instruction-following capability, compatibility with standard PEFT (LoRA/QLoRA) libraries, Apache 2.0 compliance, and optimal parameter capacity (7B-8B scale) for local execution and deployment.


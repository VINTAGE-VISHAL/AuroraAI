# ADR-0003: Clean Architecture Enforcement

## Status
Accepted

## Context
Educational AI systems involve complex pipelines of document ingestion, parsing, LLM-based parsing/synthesis, LoRA training, and evaluation. Direct coupling between these components leads to circular dependencies, makes modular testing impossible, and locks the system into single provider vendors (e.g. OpenAI/PyTorch).

## Decision
We enforce Clean Architecture rules:
1. **Domain Isolation**: Pure domain schemas live in `models/` with no direct dependencies on database libraries, web frameworks, or LLM vendors.
2. **Behavior Contracts**: High-level workflow components define their interfaces in `interfaces/` and contracts in `contracts/`.
3. **Validation Separation**: Compliance rules are isolated inside `contracts/` while active validation checks live inside `validators/`.
4. **Dependency Inversion**: Outer layers (functional modules) depend strictly on inner abstractions (`interfaces/`, `contracts/`). Implementations are registered dynamically and lookup is handled through a decoupled `ModuleRegistry`.

## Consequences
- Clean testing isolation via mocking.
- Replaceable adapters for databases, training pipelines, and LLM backends.

# ADR 0011: Dataset Studio Architecture

## Context
AuroraEngine v1.0 produces structured Knowledge Graphs and Semantic Chunks. To train educational models using LoRA fine-tuning, we require a pipeline that transforms these structured artifacts into instruction-tuning datasets. Hardcoding prompt templates and converting text raw-split style will fail to guarantee accuracy, grounding, or pedagogical variety.

## Decision
We introduce **Dataset Studio**, a modular dataset compilation subsystem, structured around these invariants:
1. **Traceability**: Every generated training example must hold a traceability mapping linking it back to source Knowledge Units, concepts, and evidence.
2. **Pedagogical Formats**: Generated datasets are composed of explicit format plugins (e.g. Tutor QA, MCQ, Flashcard, Viva, Coding Exercises).
3. **Template & Rule Decoupling**: Prompt layouts (templates) are managed separately from pedagogical content selectors (rules) using a Template Registry.
4. **Multi-Stage Validation**: Employs structural validations (e.g. completeness) and educational validations (grounding to textbook source units).
5. **Immutable Dataset Releases**: Datasets are stored as raw exports (JSONL/Parquet/ChatML), while the release manifests are immutable metadata artifacts.

## Consequences
- Dataset Studio remains independent of downstream training runtimes and upstream parser formats.
- Complete explainability is maintained: downstream models can trace every instruction prompt back to the exact paragraph source reference.

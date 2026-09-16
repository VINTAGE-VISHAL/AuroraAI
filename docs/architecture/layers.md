# Architectural Layer Definitions

AuroraEngine is structured into five distinct layer boundaries.

## L0 Infrastructure
- **Responsibility**: Provides the core runner runtime, metrics system, pipeline execution mechanics, custom exceptions, and artifact lineage models.
- **Packages**: `aurora.core`

## L1 Document Engineering
- **Responsibility**: Manages file discovery, ingestion loader interfaces, extraction classifications, standard cleaning normalizations, and structural segment parses.
- **Packages**: `aurora.ingestion`, `aurora.extraction`, `aurora.normalization`, `aurora.segmentation`

## L2 Knowledge Engineering (Future)
- **Responsibility**: Maps concept extractions, builds taxonomy links, and structures learning relationship matrices.

## L3 Dataset Engineering (Future)
- **Responsibility**: Chunks documents semantically and engineers Q&A pairs for curriculum datasets.

## L4 AI Integration (Future)
- **Responsibility**: Exports models, interfaces fine-tunings, and runs RAG retrieval evaluation benchmarks.

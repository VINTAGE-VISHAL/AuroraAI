# ADR-0010: Document Structural Segmentation Subsystem

## Context

To fine-tune domain-specific language models on educational curricula, we must decompose normalized textual documents into logical and structural components (headings, paragraphs, code blocks, lists). This ensures downstream models process cohesive, structurally coherent pieces of content instead of naive chunks.

## Decision

We establish the `Structural Segmentation` subsystem. It implements:
1. Pluggable, sequentially refined steps inheriting from `ISegmentationStep` (operating on `List[DocumentSegment]`).
2. Stable segment hashes calculated as `SHA256(document_id:segment_type:start_offset:end_offset)`.
3. Parent-child relationships mapped using heading levels.
4. Validation checks ensuring no overlapping offset ranges and complete logical text coverage.

## Consequences

- Documents are cleanly partitioned into logical segments.
- Hierarchical associations (e.g. paragraphs nested under subheadings) are preserved.
- Precise offset validation guarantees zero content corruption or data loss.

# ADR-0009: Document Normalization Subsystem

## Status
Accepted

## Context
Raw extracted text from documents contains various spacing irregularities, character encodings, and control symbols. Normalizing text is critical before segmentation, but doing so in a single giant class is brittle. Furthermore, we must establish what transforms are permitted on educational resources.

## Decision
1. **Pipeline Architecture**: Normalization is step-based. A `NormalizationPipeline` executes sequential implementations of `INormalizationStep`.
2. **Structural Preservation**: Extracted tables, images, and links must be preserved through the pipeline and carried forward in `NormalizedDocument`.
3. **Operational Scope Constraints**:
   - **Allowed**: Standardizing spacing/tabs/newlines, removing non-printable control characters, standardizing Unicode (NFC), character entity conversion.
   - **Forbidden**: Grammar changes, word replacements, semantic summarization, reordering of paragraphs.

## Consequences
- Clean separation of formatting and cleanup rules.
- Guarantees faithful source text preservation for educational accuracy.

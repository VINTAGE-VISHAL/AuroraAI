# Document Normalization Subsystem Design

## Problem Definition
How do we strip control characters, standardize whitespace, and unify Unicode text representations of extracted documents while preserving structures (tables, images, links) in an extensible way?

## Responsibilities
* **INormalizationStep**: Contract for individual cleaning rules.
* **NormalizationContext**: Configures pipeline execution (e.g. collapse whitespace, preserve Markdown) and collects metrics.
* **NormalizationPipeline**: Combines steps and converts `ExtractedDocument` to the `NORMALIZED` state `NormalizedDocument`.

## Sequence Flow
```mermaid
sequenceDiagram
    participant Pipeline
    participant Step1 as ControlCharacterNormalizer
    participant Step2 as WhitespaceNormalizer
    participant Step3 as UnicodeNormalizer

    Pipeline->>Step1: normalize(text)
    Step1-->>Pipeline: return cleaned_text
    Pipeline->>Step2: normalize(cleaned_text)
    Step2-->>Pipeline: return collapsed_text
    Pipeline->>Step3: normalize(collapsed_text)
    Step3-->>Pipeline: return standardized_text
```

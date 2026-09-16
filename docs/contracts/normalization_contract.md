# Normalization Module Contract

## Purpose
Applies formatting, character cleanups, and standards normalization to extracted document text without changing educational meaning.

## Inputs
- `ExtractedDocument`

## Outputs
- `NormalizedDocument`

## Owned Models
- `NormalizedDocument`
- `NormalizationContext`

## Exceptions
- `NormalizationError`
- `NormalizationFailedError`
- `InvalidNormalizationError`

## Pipeline
- `NormalizationPipeline` (Line endings, Control characters, Unicode NFC, Whitespace collapse).

## Extension Points
- Implement `INormalizationStep` for custom language token normalizers.

## Version History
- v1.0.0: Initial text cleaning pipeline steps.

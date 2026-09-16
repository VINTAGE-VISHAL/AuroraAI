# Concept Extraction Module Contract

## Purpose
Discovers domain concepts from structured document segments using patterns (headings, bold texts, definition prefixes), normalizes/validates candidates, and groups them into versioned collections.

## Inputs
- `StructuredDocument`

## Outputs
- `ExtractedConceptCollection`

## Owned Models
- `ExtractedConceptCollection`
- `Concept`

## Exceptions
- `ExtractionError`
- `TaxonomyError`

## Pipeline
- `ConceptExtractorPipeline`
  - `CandidateDiscoveryStep`
  - `CandidateNormalizationStep`
  - `CandidateValidationStep`
  - `ConceptAssemblyStep`

## Extension Points
- Implement `ICandidateDiscoveryStrategy` for custom document structures.

## Version History
- v1.0.0: Initial candidate discovery and normalization pipelines.

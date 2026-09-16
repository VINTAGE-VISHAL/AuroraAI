# Knowledge Graph Builder Module Contract

## Purpose
Assembles `ExtractedConceptCollection`, `KnowledgeUnitCollection`, and `ConceptRelationshipCollection` into an indexed `KnowledgeGraph`. Performs reference validations, collapses duplicate links, and computes graph topology statistics.

## Inputs
- `ExtractedConceptCollection`
- `KnowledgeUnitCollection`
- `ConceptRelationshipCollection`

## Outputs
- `KnowledgeGraph`

## Owned Models
- `KnowledgeGraph`
- `GraphStatistics`

## Exceptions
- `GraphConstructionError`
- `InvalidGraphReferenceError`

## Pipeline
- `KnowledgeGraphBuilderPipeline`
  - `GraphAssemblyStep`
  - `GraphValidationStep`
  - `GraphStatisticsStep`

## Extension Points
- Integrate custom topological analysis checkers.

## Version History
- v1.0.0: Initial multi-collection assembler and statistics pipeline.

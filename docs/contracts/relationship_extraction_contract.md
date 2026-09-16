# Relationship Extraction Module Contract

## Purpose
Discovers semantic connections (Prerequisites, Parts, Subtypes, etc.) between concepts using structural indicators, section hierarchies, linguistic phrase patterns, and co-occurrences.

## Inputs
- `ExtractedConceptCollection`
- `KnowledgeUnitCollection`

## Outputs
- `ConceptRelationshipCollection`

## Owned Models
- `ConceptRelationshipCollection`
- `ConceptRelationship`
- `RelationshipCandidate`
- `RelationshipPattern`

## Exceptions
- `RelationshipExtractionError`

## Pipeline
- `ConceptRelationshipExtractorPipeline`
  - `CandidateRelationshipDiscoveryStep`
  - `RelationshipClassificationStep`
  - `EvidenceAssociationStep`
  - `RelationshipValidationStep`
  - `CollectionAssemblyStep`

## Extension Points
- Register new linguistic patterns in the `RelationshipPattern` registry.

## Version History
- v1.0.0: Pattern-based and hierarchy-based relationship extractor.

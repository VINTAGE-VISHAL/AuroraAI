# Segmentation Module Contract

## Purpose
Slices normalized documents into logical and structural segment nodes (headings, paragraphs, code blocks) mapping their hierarchical parent/child associations.

## Inputs
- `NormalizedDocument`

## Outputs
- `StructuredDocument`

## Owned Models
- `StructuredDocument`
- `DocumentSegment`

## Exceptions
- `SegmentationError`
- `SegmentationFailedError`
- `InvalidSegmentError`

## Pipeline
- `SegmentationPipeline` (Headers, CodeBlocks, Paragraphs).

## Extension Points
- Implement `ISegmentationStep` for new structural blocks (e.g. Lists, Tables).

## Version History
- v1.0.0: Initial heading stack and offset validations.

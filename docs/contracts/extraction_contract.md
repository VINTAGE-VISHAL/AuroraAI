# Extraction Module Contract

## Purpose
Inspects RawDocument structures, classifies their document types, selects suitable extractors, and converts raw binary data into decode-safe ExtractedDocument objects.

## Inputs
- `RawDocument`

## Outputs
- `ExtractedDocument`

## Owned Models
- `ExtractedDocument`
- `DocumentDescriptor`

## Exceptions
- `ExtractionError`
- `DecoderError`
- `UnsupportedExtractionError`

## Pipeline
- `DocumentInspector`
- `DetectionPipeline`
- `ExtractorRegistry`

## Extension Points
- Implement `IDocumentExtractor` for new document file types (e.g. PDF, DOCX).
- Implement `IDocumentDetector` for magic-bytes signature classification.

## Version History
- v1.0.0: Initial extraction registry and inspector.

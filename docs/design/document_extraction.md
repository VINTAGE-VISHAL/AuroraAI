# Document Extraction Subsystem Design Document

## Problem Definition
How do we parse diverse document formats (PDF, DOCX, TXT, MD, HTML) into rich structured data (`ExtractedDocument`) in an extensible, testable, and type-safe manner?

## Responsibilities
* **DocumentInspector**: Classifies raw document bytes using magic byte signatures (and scans ZIP entry names for DOCX/Office file types).
* **ExtractorRegistry**: Registers extractor factories and maps them to `DocumentType`s.
* **IDocumentExtractor**: Defines contract containing `extract(doc: RawDocument)` and capacity metadata.

## Sequence Diagram
```mermaid
sequenceDiagram
    participant Runner
    participant Inspector as DocumentInspector
    participant Registry as ExtractorRegistry
    participant Extractor as IDocumentExtractor

    Runner->>Inspector: inspect(raw_doc)
    Inspector-->>Runner: return DocumentDescriptor
    Runner->>Registry: get_extractor_factory(descriptor.doc_type)
    Registry-->>Runner: return Extractor Class
    Runner->>Extractor: instantiate & extract(raw_doc)
    Extractor-->>Runner: return ExtractedDocument
```

## Error Model
* `ExtractionError`: Base class.
* `UnsupportedExtractionError`: Raised when no extractor is registered for a type.
* `ExtractionFailedError`: Raised if extraction crashes.
* `CorruptedDocumentError`: Raised if document magic bytes match but payload parser fails (corrupt file).
* `DecoderError`: Raised on text decoding errors (e.g. invalid UTF-8).

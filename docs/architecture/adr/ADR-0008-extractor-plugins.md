# ADR-0008: Document Extractor Plugin Architecture

## Status
Accepted

## Context
AuroraEngine must parse text, tables, and images from multiple document formats (PDF, DOCX, TXT, MD, HTML). Coupling parsing logic into one class violates the Single Responsibility and Open/Closed Principles.

## Decision
1. **Dynamic Classification**: We introduce a `DocumentInspector` that inspects raw bytes and magic signatures (e.g. zip sub-inspectors) to classify formats, returning a `DocumentDescriptor`.
2. **Pluggable Extractors**: Every parser implements the `IDocumentExtractor` interface and registers as a class/factory in the `ExtractorRegistry`.
3. **Registry Isolation**: Downstream processing queries the registry for the appropriate extractor factory based on the `DocumentDescriptor.doc_type`.

## Consequences
- Clean alignment with Open/Closed Principle.
- Formats can be added independently as plugins.

# Ingestion Module Contract

## Purpose
Exposes facilities to scan, register, and stream byte data from the filesystem or external sources, producing validated RawDocument representations.

## Inputs
- Filesystem directories, files, or URIs.

## Outputs
- `RawDocument` (with associated metadata).

## Owned Models
- `RawDocument`
- `FileMetadata`
- `SourceDocument`
- `SourceMetadata`

## Exceptions
- `DocumentLoadError`
- `PermissionDeniedError`
- `UnreadableDocumentError`
- `UnsupportedDocumentError`

## Pipeline
- `FileScanner`
- `SourceRegistry`
- `DocumentLoader`

## Extension Points
- Implement custom file scanners or URI loaders.

## Version History
- v1.0.0: Initial ingestion pipeline design.

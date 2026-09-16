# ADR-0006: Ingestion Document Lifecycle

## Status
Accepted

## Context
Downstream parsing, normalization, and segmenting components must have clear expectations of document states. Mutating state implicitly leads to race conditions and bugs.

## Decision
We enforce a strict, one-way state transition machine for documents:
* **DISCOVERED**: Detected by scanner.
* **REGISTERED**: Saved in registry with checksum and metadata.
* **LOADED**: Loaded as immutable bytes (`RawDocument`).
* **EXTRACTED**: Extracted into clean structured text and tables.
* **NORMALIZED**: Formatted and cleaned of noise.
* **SEGMENTED**: Segmented into learning chunks.

These states are mapped to an explicit `DocumentState` Enum.

## Consequences
- Prevents skipping stages (e.g. attempting to extract a document before it is loaded).
- Guarantees pipeline transparency.

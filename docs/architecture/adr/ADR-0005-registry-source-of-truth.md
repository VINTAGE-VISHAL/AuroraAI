# ADR-0005: Source Registry as the Single Source of Truth

## Status
Accepted

## Context
Downstream modules (parsers, extractors, trainers) need to reference original educational sources. Direct file access leads to data drift, loose consistency, and locks the application to local disk paths.

## Decision
1. **Single Access Gate**: `SourceRegistry` is the single source of truth for locating documents and retrieving metadata.
2. **Abstract URIs**: Document references are made via URIs (e.g. `file://`, `s3://`), not hardcoded local paths.
3. **Downstream Compliance**: No downstream module (e.g. Preprocessing, Understanding) may scan filesystems or storage directories directly. They must query the registry.

## Consequences
- Guarantees decoupling from physical storage layer.
- Enables simple database or cloud backends in the future.
- Downstream modules remain pure functional transformers.

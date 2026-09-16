# ADR-0004: Semantic Versioning Strategy

## Status
Accepted

## Context
As AuroraEngine matures from an initial prototype to a research-grade framework, tracking release stability and API breaks is vital.

## Decision
We adopt Semantic Versioning (SemVer) with custom milestones mapped to key framework releases:
* `0.x.x`: Active design and implementation phase.
* `1.0.0`: Ingestion framework (Source Registry, Corpus Loader, Normalization).
* `2.0.0`: Curriculum understanding and model mapping (Concept dependency graphs).
* `3.0.0`: Educational dataset generation.
* `4.0.0`: Training framework (LoRA adapter configurations).
* `5.0.0`: Deployment framework (Local/cloud inference serving).

## Consequences
Any backward-incompatible API changes within a major milestone require bumping the major version number.

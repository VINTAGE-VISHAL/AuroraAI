# ADR-0007: Immutable Pipeline Stages

## Status
Accepted

## Context
Educational document processing involves sequential cleaning, chunking, and validation. Mutating document instances in-place makes pipeline steps dependent on call order, complicates multi-threaded/distributed execution, and breaks state histories.

## Decision
1. **Pipeline Immutability**: Every pipeline component must consume an immutable document model and return a *new* immutable document model representing the next lifecycle state.
2. **Frozen Model Schemas**: Pydantic models (such as `RawDocument`) will be configured as read-only (`frozen=True`) to enforce this at compile/runtime.

## Consequences
- Simplifies tracing, caching, and debugging processing runs.
- Facilitates parallelization.

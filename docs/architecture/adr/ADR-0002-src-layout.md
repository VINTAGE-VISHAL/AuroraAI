# ADR-0002: Use of src/ Package Layout

## Status
Accepted

## Context
Standardizing directory structures prevents namespaces contamination, avoids accidental import resolving errors from the workspace root during development, and ensures clean package distribution.

## Decision
We enforce the standard `src/` layout. All core source code resides under `src/aurora/`. Test scripts reside separately under `tests/`.

## Consequences
- Requires installing the package in editable mode (`pip install -e .`) for local imports to resolve during testing.
- Aligns layout with modern Python build backends (e.g., hatchling, setuptools).

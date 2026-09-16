# ADR-0001: Project Constitution Adopted

## Status
Accepted

## Context
AuroraEngine is designed as a research-grade educational AI framework rather than a generic chatbot or LLM wrapper. To prevent code rot and maintain structural integrity during expansion, clear rules are required.

## Decision
We formally adopt the **AuroraEngine Project Constitution** as workspace rules located at `.agents/AGENTS.md`. Key tenets include:
* Clean Architecture principles.
* Interface-first development.
* SOLID compliance.
* Dependency injection.
* Strict "No implementation without an interface and design document" gate policy.

## Consequences
All future code contributions and sub-agents must adhere to these policies. Code ignoring these tenets will be flagged and rejected.

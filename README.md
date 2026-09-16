# AuroraEngine

> **The Foundation for Trustworthy Educational AI**  
> *A Modular Educational AI Engine for Building Domain-Specific Language Models*

---

## Vision Statement

**AuroraEngine** is a modular, research-grade educational AI framework that transforms trusted educational resources into domain-specific language models through structured ingestion, curriculum understanding, knowledge extraction, dataset engineering, LoRA training, evaluation, and deployment. Every component is independent, extensible, and designed around clean architecture principles.

---

## Repository Structure

```
AuroraEngine/
│
├── src/
│   └── aurora/
│       ├── core/           # Foundational components (exceptions, logging, base, etc.)
│       ├── config/         # Structured settings loaders and schemas
│       ├── models/         # Centralized domain models (document, curriculum, etc.)
│       ├── interfaces/     # Interface contracts for modular pipeline phases
│       ├── registry/       # Module, adapter, and plugin registries
│       ├── services/       # Coordination services across modules
│       ├── storage/        # FAISS, Chroma, metadata, and graph storage orchestration
│       ├── pipeline/       # Pipeline builder and execution orchestration
│       │
│       ├── ingestion/      # Data/source resource ingestion phase
│       ├── preprocessing/  # Parsing, cleaning, and text splitting phase
│       ├── understanding/  # Knowledge extraction and curriculum analysis phase
│       ├── dataset/        # QA pairs and instruction tuning dataset generation
│       ├── training/       # Fine-tuning and LoRA adapter training phase
│       ├── evaluation/     # Trustworthiness, accuracy, and syllabus alignment evaluation
│       ├── deployment/     # Local/cloud inference server deployment
│       └── __init__.py
│
├── tests/                  # Mirrored test suite mirroring the src/ layout
├── docs/                   # Framework design and research documentation
├── examples/               # End-to-end framework usage examples
├── scripts/                # Automation and developer utility scripts
├── .github/                # CI/CD Workflows
├── pyproject.toml          # Packaging and tool configurations
├── README.md               # Project documentation
├── LICENSE                 # MIT License
└── .gitignore              # Python git ignore rules
```

---

## Development Philosophy

Every line of code in AuroraEngine adheres to the following principles:

1. **Interface-first development**: Code to abstractions, not implementations. Interfaces must be defined before code is written.
2. **SOLID principles**: High cohesion, low coupling, single responsibility.
3. **Clean Architecture**: Decouple domain models, interfaces, and business logic from external libraries, storage backends, or frameworks.
4. **Dependency Injection**: Inject requirements explicitly to facilitate mock testing.
5. **Configuration-driven design**: Behavior should be parameterized via structured configuration interfaces.
6. **Strong typing**: Static typing with `mypy` check enforcement across all source files.
7. **Comprehensive testing**: High coverage testing mirrored across the suite.
8. **Research-grade documentation**: Every component should explain *why* it is designed this way alongside code usage.
9. **Reusable modules**: Avoid global state; keep components self-contained.
10. **No shortcuts**: Write production-quality code from the start.

### The Aurora Policy
> [!IMPORTANT]
> **No implementation without an interface and a design document.**  
> For every major module, the workflow must be:
> 1. Define the problem.
> 2. Specify the interface (public API/contracts).
> 3. Design the data models.
> 4. Implement the module.
> 5. Write unit tests.
> 6. Integrate it into the pipeline.

---

## Getting Started

### Prerequisites

- Python `>= 3.10`

### Installation

To install the development dependencies:

```bash
pip install -e ".[dev]"
```

### Linting and Testing

To format and lint the codebase:

```bash
ruff check .
ruff format .
```

To run the test suite:

```bash
pytest
```

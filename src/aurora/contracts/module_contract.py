"""Contract definition for all AuroraEngine pipeline modules."""

class ModuleContract:
    """Defines requirements, invariants, and behaviors expected of every functional module.

    Invariants:
        1. Every module must accept a configuration Settings object on
           initialization (Dependency Injection).
        2. Modules must provide deterministic or seeded output for reproducible results.
        3. Modules must use the core logging utility rather than prints.
        4. Module errors must wrap external exceptions in subclasses of AuroraError.
        5. Modules must offer standard lifecycle operations (e.g. `run` method).
    """
    pass

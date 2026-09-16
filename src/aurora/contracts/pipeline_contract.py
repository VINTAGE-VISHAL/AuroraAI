"""Contract definition for pipeline execution states."""

class PipelineContract:
    """Defines requirements, invariants, and transitions for pipeline state.

    Invariants:
        1. Components in the pipeline must execute sequentially.
        2. Output types of step N must exactly match input types expected by step N+1.
        3. Initial input data cannot be null.
        4. Runtime exceptions in any component must abort execution cleanly
           without leaving lockfiles.
    """
    pass

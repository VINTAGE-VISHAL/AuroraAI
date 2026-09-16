"""Validator for pipeline structures."""

from aurora.core.exceptions import InterfaceError
from aurora.pipeline.pipeline import Pipeline


def validate_pipeline(pipeline: Pipeline) -> None:
    """Validate pipeline complies with PipelineContract rules."""
    if not pipeline.components:
        raise InterfaceError("Pipeline must contain at least one execution component.")

"""Utility to trigger pipeline runs from configuration settings."""

from aurora.config.settings import Settings
from aurora.pipeline.builder import PipelineBuilder
from aurora.pipeline.pipeline import Pipeline


def create_default_pipeline(settings: Settings) -> Pipeline:
    """Helper to assemble a default end-to-end Aurora pipeline."""
    return (
        PipelineBuilder(settings)
        .add_component("ingestion")
        .add_component("preprocessing")
        .add_component("segmentation")
        .add_component("corpus")
        .add_component("training_input_adapter")
        .add_component("training")
        .add_component("evaluation")
        .build()
    )

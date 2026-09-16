from pathlib import Path

from aurora.config.settings import Settings
from aurora.pipeline.runner import create_default_pipeline


def test_default_pipeline_execution(default_settings: Settings, tmp_path: Path) -> None:
    """Verify that all default steps in the pipeline execute correctly in sequence."""
    pipeline = create_default_pipeline(default_settings)

    # Create dummy subject folder and file to avoid scan directory errors
    math_dir = tmp_path / "math"
    math_dir.mkdir()
    dummy_file = math_dir / "algebra.txt"
    dummy_file.write_text("algebra principles")

    # Set output path to temporary folder to avoid overwriting production data
    default_settings.corpus.output_path = str(tmp_path / "training.jsonl")

    # Run pipeline starting with raw text path string
    results = pipeline.execute(str(tmp_path))

    assert "accuracy" in results
    assert "trustworthiness" in results
    assert results["accuracy"] > 0.0
    assert results["trustworthiness"] > 0.0


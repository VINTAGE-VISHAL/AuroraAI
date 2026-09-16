"""Unit tests for the CheckpointManager Phase D component."""

import json
import os
from aurora.training.checkpoint_manager import CheckpointManager


def test_checkpoint_manager_scan_and_prune(tmp_path) -> None:
    """Verify scanning valid checkpoints and pruning older entries works correctly."""
    output_dir = tmp_path / "checkpoints"
    output_dir.mkdir()

    # Create mock checkpoint subdirs
    c10 = output_dir / "checkpoint-10"
    c20 = output_dir / "checkpoint-20"
    c30 = output_dir / "checkpoint-30"

    for cp_dir in (c10, c20, c30):
        cp_dir.mkdir()
        # Create required files
        (cp_dir / "adapter_config.json").touch()
        (cp_dir / "adapter_model.safetensors").touch()

    # Write trainer state to checkpoint-20
    state_data = {
        "log_history": [
            {"step": 20, "epoch": 0.5, "loss": 0.45}
        ]
    }
    with open(c20 / "trainer_state.json", "w", encoding="utf-8") as f:
        json.dump(state_data, f)

    manager = CheckpointManager()

    # Scan and verify sorting
    checkpoints = manager.scan(str(output_dir))
    assert len(checkpoints) == 3
    assert checkpoints[0].global_step == 10
    assert checkpoints[1].global_step == 20
    assert checkpoints[1].epoch == 0  # 0.5 cast to int is 0
    assert checkpoints[1].loss == 0.45
    assert checkpoints[2].global_step == 30

    # Prune and keep last 2
    manager.prune(checkpoints, keep_last=2)
    
    assert not os.path.exists(c10)
    assert os.path.exists(c20)
    assert os.path.exists(c30)

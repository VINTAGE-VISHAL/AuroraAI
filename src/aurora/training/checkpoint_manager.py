"""CheckpointManager implementation for Phase D lifecycle operations."""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import ICheckpointManager
from aurora.models import CheckpointInfo
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("checkpoint_manager")
class CheckpointManager(ICheckpointManager):
    """Scans, validates, and prunes training checkpoints from output directories."""

    def scan(self, output_dir: str) -> List[CheckpointInfo]:
        """Scans the output directory for valid Hugging Face adapter checkpoints."""
        if not os.path.exists(output_dir):
            return []

        checkpoints: List[CheckpointInfo] = []
        try:
            for entry in os.listdir(output_dir):
                entry_path = os.path.join(output_dir, entry)
                if not os.path.isdir(entry_path) or not entry.startswith("checkpoint-"):
                    continue

                # Validate required QLoRA adapter configuration and weight files
                has_config = os.path.exists(os.path.join(entry_path, "adapter_config.json"))
                has_weights = os.path.exists(os.path.join(entry_path, "adapter_model.safetensors")) or \
                              os.path.exists(os.path.join(entry_path, "adapter_model.bin"))

                if not (has_config and has_weights):
                    continue

                # Extract step number from name
                try:
                    step = int(entry.split("-")[1])
                except (IndexError, ValueError):
                    continue

                epoch = 0
                loss_val = 0.0

                # Attempt to parse trainer_state.json for accurate epoch and loss metrics
                state_path = os.path.join(entry_path, "trainer_state.json")
                if os.path.exists(state_path):
                    try:
                        with open(state_path, "r", encoding="utf-8") as f:
                            state_data = json.load(f)
                            for log in state_data.get("log_history", []):
                                if log.get("step") == step:
                                    epoch = int(float(log.get("epoch", epoch)))
                                    loss_val = float(log.get("loss", log.get("train_loss", loss_val)))
                            if epoch == 0 and "epoch" in state_data:
                                epoch = int(float(state_data["epoch"]))
                    except Exception:
                        pass  # Fall back to default parameters if json parsing fails

                created_time = os.path.getmtime(entry_path)
                created_dt = datetime.fromtimestamp(created_time)

                checkpoints.append(
                    CheckpointInfo(
                        checkpoint_name=entry,
                        path=entry_path,
                        epoch=epoch,
                        global_step=step,
                        loss=loss_val,
                        timestamp=created_dt,
                    )
                )
        except Exception as e:
            raise InterfaceError(f"Failed to scan checkpoint directory '{output_dir}': {e}")

        # Return checkpoints sorted ascending by step number
        checkpoints.sort(key=lambda c: c.global_step)
        return checkpoints

    def prune(self, checkpoints: List[CheckpointInfo], keep_last: int) -> None:
        """Removes older checkpoints to manage storage footprint, keeping the last N checkpoints."""
        if len(checkpoints) <= keep_last or keep_last < 0:
            return

        # Prune oldest checkpoints (checkpoints are assumed to be sorted ascending by step)
        to_prune = checkpoints[:-keep_last]
        for checkpoint in to_prune:
            if os.path.exists(checkpoint.path):
                try:
                    shutil.rmtree(checkpoint.path)
                except Exception as e:
                    raise InterfaceError(f"Failed to prune checkpoint at '{checkpoint.path}': {e}")

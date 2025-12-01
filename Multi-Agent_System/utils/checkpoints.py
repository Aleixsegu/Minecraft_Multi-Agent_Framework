# utils/checkpoints.py

import json
from pathlib import Path


def save_checkpoint(path: str, data: dict):
    """
    Saves the agent's internal context to a JSON file.
    Required for pause/resume/stop behavior as specified in the assignment.
    """
    file_path = Path(path)
    file_path.parent.mkdir(exist_ok=True, parents=True)

    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[CHECKPOINT ERROR] Could not save checkpoint: {e}")


def load_checkpoint(path: str) -> dict:
    """
    Loads the agent's context from a JSON checkpoint file.
    If the file does not exist, returns an empty dictionary.
    """
    file_path = Path(path)

    if not file_path.exists():
        return {}

    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[CHECKPOINT ERROR] Could not load checkpoint: {e}")
        return {}

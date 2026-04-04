import yaml
import os
from pathlib import Path
from typing import Any


def load_config(path: str = "configs/config.yaml") -> dict[str, Any]:
    """Load and return the master YAML config with env-var substitution."""
    with open(Path(path), "r") as f:
        raw = f.read()

    # Substitute ${VAR} placeholders from environment
    for key, value in os.environ.items():
        raw = raw.replace(f"${{{key}}}", value)

    return yaml.safe_load(raw)


CONFIG = load_config()
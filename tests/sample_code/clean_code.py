
import json
import os
from pathlib import Path


def load_config(filepath: str) -> dict:
    """Load and return config from a JSON file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config: {e}")


def get_setting(config: dict, key: str, default=None):
    """Safely retrieve a setting with an optional default."""
    return config.get(key, default)


def divide(a: float, b: float) -> float:
    """Divide a by b, raising an error if b is zero."""
    if b == 0:
        raise ZeroDivisionError("Divisor cannot be zero.")
    return a / b


"""Configuration management for Project Chronos."""

from pathlib import Path
import tomllib


class ConfigurationError(Exception):
    """Raised when Chronos configuration is invalid."""


def load_config(path):
    """Load and validate a Chronos TOML configuration file."""
    path = Path(path)

    try:
        with path.open("rb") as file:
            config = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(
            f"Cannot load configuration: {exc}"
        ) from exc

    if not isinstance(config.get("node"), dict):
        raise ConfigurationError("Missing [node] section")

    node_id = config["node"].get("id")
    if not isinstance(node_id, str) or not node_id.strip():
        raise ConfigurationError("Invalid node ID")

    return config


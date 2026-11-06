
"""Project Chronos — Core application entry point."""

import platform
import sys
from pathlib import Path

# Support module and direct script execution.
if __package__:
    from .config import ConfigurationError, load_config
    from .logging_setup import setup_logging
    from .node_identity import NodeIdentityError, load_or_create_identity
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from software.core.config import ConfigurationError, load_config
    from software.core.logging_setup import setup_logging
    from software.core.node_identity import (
        NodeIdentityError,
        load_or_create_identity,
    )


CHRONOS_VERSION = "0.1.0"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT / "software" / "config" / "chronos.example.toml"
)


def get_system_info():
    """Return basic information about the running system."""
    return {
        "chronos_version": CHRONOS_VERSION,
        "python_version": platform.python_version(),
        "operating_system": platform.system(),
        "architecture": platform.machine(),
    }


def main(config_path=None):
    """Initialize the Chronos Core application."""

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    try:
        config = load_config(config_path)
    except ConfigurationError as exc:
        print(f"Chronos configuration error: {exc}", file=sys.stderr)
        return 1

    node = config["node"]
    core = config.get("core", {})
    log_level = core.get("log_level", "INFO")

    try:
        logger = setup_logging(
            log_directory=PROJECT_ROOT / "logs",
            log_level=log_level,
        )
    except (OSError, ValueError) as exc:
        print(f"Chronos logging error: {exc}", file=sys.stderr)
        return 1

    try:
        identity = load_or_create_identity(
            PROJECT_ROOT / "data" / "node" / "identity.json"
        )
    except NodeIdentityError as exc:
        logger.error("Node identity initialization failed: %s", exc)
        return 1

    info = get_system_info()

    logger.info("Chronos Core starting")
    logger.info("Configured Node ID: %s", node["id"])
    logger.info("Persistent Node UUID: %s", identity["node_id"])
    logger.info("Chronos version: %s", info["chronos_version"])
    logger.info("Operating system: %s", info["operating_system"])
    logger.info("Python version: %s", info["python_version"])
    logger.info("Chronos Core initialized successfully")

    return 0


if __name__ == "__main__":
    sys.exit(main())


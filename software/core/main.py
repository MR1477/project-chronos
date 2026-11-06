
"""Project Chronos — Core application entry point."""

import platform
import sys

CHRONOS_VERSION = "0.1.0"


def get_system_info():
    """Return basic information about the running system."""
    return {
        "chronos_version": CHRONOS_VERSION,
        "python_version": platform.python_version(),
        "operating_system": platform.system(),
        "architecture": platform.machine(),
    }


def main():
    """Start the Chronos Core application."""
    info = get_system_info()

    print("=" * 40)
    print("PROJECT CHRONOS")
    print("=" * 40)
    print(f"Chronos Version : {info['chronos_version']}")
    print(f"Python Version  : {info['python_version']}")
    print(f"Operating System: {info['operating_system']}")
    print(f"Architecture    : {info['architecture']}")
    print("=" * 40)
    print("Chronos Core initialized successfully.")


if __name__ == "__main__":
    main()


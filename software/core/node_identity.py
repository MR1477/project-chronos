
"""Persistent node identity management for Project Chronos."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class NodeIdentityError(Exception):
    """Raised when a node identity cannot be loaded or created."""


def load_or_create_identity(identity_path):
    """Load a persistent node identity or create one if absent."""

    path = Path(identity_path)

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))

            if not isinstance(data, dict):
                raise ValueError("Identity must be a JSON object")

            node_id = str(uuid.UUID(data["node_id"]))
            created_at = data["created_at"]

            if not isinstance(created_at, str):
                raise ValueError("Invalid creation timestamp")

            datetime.fromisoformat(created_at)

            return {
                "node_id": node_id,
                "created_at": created_at,
            }

        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise NodeIdentityError(
                f"Invalid node identity file: {exc}"
            ) from exc

    identity = {
        "node_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(identity, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise NodeIdentityError(
            f"Cannot create node identity: {exc}"
        ) from exc

    return identity


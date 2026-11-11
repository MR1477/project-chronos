"""Experiment 001: a local, source-grounded scientific notebook."""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "learning" / "experiment001.sqlite3"
SOURCE_TITLE = "A Brief History of Time"
SOURCE_AUTHOR = "Stephen Hawking"
SSH_TARGET = "pi@pi.local"
RETRYABLE_SSH_ERRORS = (
    "connection refused",
    "connection timed out",
    "operation timed out",
    "no route to host",
    "network is unreachable",
)


def required_text(record, field):
    value = record.get(field) if isinstance(record, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty text for {field}")
    return value.strip()


def required_records(record, field):
    value = record.get(field) if isinstance(record, dict) else None
    if not isinstance(value, list) or not value:
        raise ValueError(f"Expected a non-empty list for {field}")
    return value


def build_notebook(manifest):
    source = {
        "title": SOURCE_TITLE,
        "author": SOURCE_AUTHOR,
        "edition": required_text(manifest, "edition"),
        "provenance": required_text(manifest, "provenance"),
    }
    chapters = []
    for chapter in required_records(manifest, "chapters"):
        title = required_text(chapter, "title")
        notes = []
        for passage in required_records(chapter, "passages"):
            locator = required_text(passage, "locator")
            body = required_text(passage, "text")
            first_sentence = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)[0]
            excerpt = first_sentence
            if len(excerpt) > 350:
                excerpt = excerpt[:349].rstrip() + "…"
            notes.append({
                "locator": locator,
                "text": body,
                "excerpt": excerpt,
                "question": f"What does the passage at {locator} say about the idea in this excerpt?",
            })
        chapters.append({"title": title, "notes": notes})

    # Hash the inputs, so revisions keep their own notebooks and repeat imports
    # preserve the stored notes even if the extraction algorithm changes.
    inputs = {
        "source": source,
        "chapters": [
            {
                "title": chapter["title"],
                "passages": [
                    {"locator": note["locator"], "text": note["text"]}
                    for note in chapter["notes"]
                ],
            }
            for chapter in chapters
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(inputs, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "id": fingerprint,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "chapters": chapters,
    }


def load_notebook(connection, notebook_id):
    row = connection.execute(
        "SELECT notebook FROM experiment001 WHERE id = ?", (notebook_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"No notebook with ID {notebook_id}")
    return json.loads(row[0])


def ingest(database, source_path):
    notebook = build_notebook(json.loads(source_path.read_text(encoding="utf-8")))
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS experiment001 "
                "(id TEXT PRIMARY KEY NOT NULL, notebook TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO experiment001 (id, notebook) VALUES (?, ?) "
                "ON CONFLICT (id) DO NOTHING",
                (notebook["id"], json.dumps(notebook)),
            )
            return load_notebook(connection, notebook["id"])


def search_notebook(notebook, query):
    terms = set(re.findall(r"\w+", query.casefold()))
    if not terms:
        raise ValueError("Enter at least one search term")
    matches = []
    for chapter in notebook["chapters"]:
        for note in chapter["notes"]:
            words = set(re.findall(r"\w+", note["text"].casefold()))
            score = len(terms & words)
            if score:
                matches.append((score, {
                    "source": notebook["source"],
                    "chapter": chapter["title"],
                    **note,
                }))
    matches.sort(key=lambda match: match[0], reverse=True)
    return [note for _, note in matches]


def check_connection(*, attempts, run=subprocess.run, pause=time.sleep, report=print):
    """Probe authenticated SSH and retry only transient connection failures."""
    if attempts < 1:
        raise ValueError("Use at least one connection attempt")
    command = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "ConnectTimeout=5", "-o", "ConnectionAttempts=1", SSH_TARGET, "true",
    ]
    for attempt in range(1, attempts + 1):
        try:
            result = run(
                command, capture_output=True, text=True, timeout=10,
                env={**os.environ, "LC_ALL": "C"},
            )
            if result.returncode == 0:
                report(f"{SSH_TARGET} connected over authenticated SSH.")
                return True
            detail = result.stderr.strip() or f"SSH exited with {result.returncode}"
            retryable = result.returncode == 255 and any(
                error in detail.lower() for error in RETRYABLE_SSH_ERRORS
            )
            if not retryable:
                report(f"SSH check failed for {SSH_TARGET}: {detail}")
                return False
        except subprocess.TimeoutExpired:
            detail = "SSH probe timed out"

        report(
            f"SSH unreachable at {SSH_TARGET} (attempt {attempt}/{attempts}): "
            f"{detail}. Power state is unknown."
        )
        if attempt < attempts:
            pause(5)
    return False


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Chronos Experiment 001")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Local notebook database")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest_parser = commands.add_parser("ingest", help="Build a notebook from a local source manifest")
    ingest_parser.add_argument("source", type=Path)
    show_parser = commands.add_parser("show", help="Read a saved notebook")
    show_parser.add_argument("id")
    search_parser = commands.add_parser("search", help="Retrieve cited passages by keyword")
    search_parser.add_argument("id")
    search_parser.add_argument("query")
    probe_parser = commands.add_parser("probe", help="Check authenticated SSH to the Raspberry Pi")
    probe_parser.add_argument("--attempts", type=int, choices=range(1, 11), default=1)
    args = parser.parse_args(argv)

    try:
        if args.command == "probe":
            return 0 if check_connection(attempts=args.attempts) else 1

        if args.command == "ingest":
            result = ingest(args.db, args.source)
        else:
            uri = args.db.resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                result = load_notebook(connection, args.id)
            if args.command == "search":
                result = search_notebook(result, args.query)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Experiment 001: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(cli())

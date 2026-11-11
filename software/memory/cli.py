"""Command-line access to Chronos scientific memory."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .knowledge import KnowledgeStore
from .study_notes import load_study_notes


DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "memory" / "knowledge.sqlite3"


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Chronos scientific memory")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="Import a cited Markdown study file")
    ingest.add_argument("file", type=Path)
    search = commands.add_parser("search", help="Find stored notes by topic")
    search.add_argument("query")
    ask = commands.add_parser("ask", help="Answer with cited extracts from stored notes")
    ask.add_argument("question")
    args = parser.parse_args(argv)

    store = KnowledgeStore(args.db)
    try:
        if args.command == "ingest":
            result = store.ingest(load_study_notes(args.file))
        elif args.command == "search":
            result = store.search(args.query)
        else:
            result = store.ask(args.question)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Memory: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(cli())

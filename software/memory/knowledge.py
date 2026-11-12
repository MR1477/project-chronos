"""Store scientific notes in SQLite and retrieve citation-grounded evidence."""

import re
import sqlite3
from contextlib import closing
from dataclasses import astuple
from pathlib import Path

from .study_notes import StudyDocument


# Question scaffolding and common function words have little retrieval value.
QUERY_STOP_WORDS = frozenset("""
    a an and are as at be been by can contribute contribution contributions could did do does
    for from had has have how i in is it its me of on or our s should tell that the their
    them they this to understanding was were what when where which who why will with would
""".split())
WORD = re.compile(r"[^\W_]+")
NO_EVIDENCE = "The stored notes do not contain enough evidence to answer this question."


def words(text):
    return set(WORD.findall(text.casefold()))


class KnowledgeStore:
    def __init__(self, database: Path):
        self.database = database

    def ingest(self, document: StudyDocument):
        """Insert a document and all its notes together, once per file revision."""
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS study_documents (
                    id TEXT PRIMARY KEY NOT NULL,
                    source TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS study_notes (
                    document_id TEXT NOT NULL REFERENCES study_documents(id),
                    note_id TEXT NOT NULL,
                    chapter TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    citation_label TEXT NOT NULL,
                    citation_url TEXT NOT NULL,
                    PRIMARY KEY (document_id, note_id)
                )
            """)
            inserted = connection.execute(
                "INSERT INTO study_documents VALUES (?, ?) ON CONFLICT (id) DO NOTHING",
                (document.document_id, document.source),
            )
            if inserted.rowcount:
                connection.executemany(
                    "INSERT INTO study_notes VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [(document.document_id, *astuple(note)) for note in document.notes],
                )
        return {"document_id": document.document_id, "notes": len(document.notes)}

    def _ranked_matches(self, query_terms):
        if not self.database.exists():
            return []
        uri = self.database.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            rows = connection.execute("""
                SELECT n.document_id, n.note_id, n.chapter, n.title, n.body,
                       n.citation_label, n.citation_url, d.source
                FROM study_notes AS n
                JOIN study_documents AS d ON d.id = n.document_id
                ORDER BY n.document_id, length(n.note_id), n.note_id
            """)
            matches = []
            for doc_id, note_id, chapter, title, body, label, url, source in rows:
                overlap = query_terms & words(f"{title} {body}")
                if overlap:
                    matches.append((overlap, {
                        "document_id": doc_id,
                        "note_id": int(note_id),
                        "chapter": chapter,
                        "title": title,
                        "text": body,
                        "source": source,
                        "citation": {"label": label, "url": url},
                    }))
        matches.sort(key=lambda match: len(match[0]), reverse=True)
        return matches

    def search(self, query):
        return [note for _, note in self._ranked_matches(query_terms(query))]

    def ask(self, question):
        remaining = query_terms(question)
        evidence = []
        for overlap, note in self._ranked_matches(remaining):
            if overlap & remaining:
                evidence.append(note)
                remaining -= overlap
                if not remaining:
                    break
        if remaining:
            return {"status": "insufficient_evidence", "answer": NO_EVIDENCE, "evidence": []}

        return {"status": "supported", "answer": render_evidence(evidence), "evidence": evidence}


def render_evidence(evidence):
    answer = []
    for note in evidence:
        citation = note["citation"]
        answer.append(
            f'**{note["title"]}** {note["text"]} '
            f'[{citation["label"]}]({citation["url"]})'
        )
    return "\n\n".join(answer)


def query_terms(query):
    terms = words(query) - QUERY_STOP_WORDS
    if not terms:
        raise ValueError("Enter a query with at least one topic word")
    return terms

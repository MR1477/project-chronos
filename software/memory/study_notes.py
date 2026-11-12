"""Read the cited, numbered Markdown study-note format used by Chronos."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


NOTE = re.compile(
    r"(?P<id>[1-9][0-9]*)\.\s+\*\*(?P<title>.+?)\*\*\s+"
    r"(?P<text>.+?)\s+\[(?P<label>[^\[\]]+)\]\((?P<url>[^\s()]+)\)"
)


@dataclass(frozen=True)
class StudyNote:
    note_id: str
    chapter: str
    title: str
    text: str
    citation_label: str
    citation_url: str


@dataclass(frozen=True)
class StudyDocument:
    document_id: str
    source: str
    notes: tuple[StudyNote, ...]


def load_study_notes(path: Path) -> StudyDocument:
    """Load and validate all numbered notes before opening the database."""
    raw = path.read_bytes()
    source = ""
    chapter = ""
    notes = []
    note_ids = set()

    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        line = line.strip()
        if line.startswith("**Source** —"):
            if source:
                raise ValueError(f"Line {line_number}: duplicate source")
            source = line.removeprefix("**Source** —").strip()
            if not source:
                raise ValueError(f"Line {line_number}: missing source description")
        elif line.startswith("## "):
            heading = line.removeprefix("## ")
            chapter = heading if heading.casefold().startswith("chapter ") else ""
        elif chapter and re.match(r"\d+[.)](?:\s|$)", line):
            match = NOTE.fullmatch(line)
            if not match:
                raise ValueError(f"Line {line_number}: expected a numbered note with a citation")
            note_id, title, body, label, url = match.groups()
            citation = urlsplit(url)
            if citation.scheme not in ("https", "http") or not citation.hostname:
                raise ValueError(f"Line {line_number}: expected an HTTP or HTTPS citation URL")
            if not all(value.strip() for value in (title, body, label)):
                raise ValueError(f"Line {line_number}: note text, title and citation label are required")
            if note_id in note_ids:
                raise ValueError(f"Line {line_number}: duplicate note identifier {note_id}")
            note_ids.add(note_id)
            notes.append(StudyNote(note_id, chapter, title.strip(), body.strip(), label, url))

    if not source or not notes:
        raise ValueError("Expected a source description and at least one cited chapter note")
    return StudyDocument(hashlib.sha256(raw).hexdigest(), source, tuple(notes))

# Chronos Memory

**Module:** `software/memory/`  
**Version:** 0.1.0  
**Status:** Experiment 001 pilot

## 1. Purpose

Chronos Memory is the persistent knowledge and research preservation system of Project Chronos.

Its primary responsibility is to ensure that scientific knowledge, research history, observations, decisions, and accumulated experience remain available independently of the AI models, hardware, and software versions used by Chronos.

The knowledge accumulated by Chronos must never depend on the continued existence of a particular AI model.

## 2. Main Responsibilities

- Store and retrieve scientific knowledge.
- Preserve research documents, books, articles, and references.
- Maintain structured records of experiments and observations.
- Preserve hypotheses, conclusions, and rejected explanations.
- Record research decisions and their reasoning.
- Maintain historical versions of important records.
- Support semantic and keyword-based information retrieval.
- Maintain metadata, timestamps, and source attribution.
- Support synchronization between distributed Chronos nodes.
- Detect corrupted or inconsistent records.

## 3. Knowledge Organization

Chronos Memory should support several categories of information:

1. **Scientific Knowledge:** Established scientific information and verified findings.
2. **Research Materials:** Books, papers, datasets, and technical documents.
3. **Hypotheses:** Proposed explanations awaiting verification.
4. **Experiments:** Experimental procedures, observations, and results.
5. **System Knowledge:** Software architecture, hardware configurations, and operational instructions.
6. **Historical Records:** Decisions, previous versions, failures, and development history.
7. **Communication Records:** Messages and research exchanges between Chronos nodes and generations.

Each record should preserve its source, creation time, version, verification status, and relevant references whenever applicable.

## 4. Long-Term Preservation

Memory must be independent of individual storage providers and hardware devices.

The architecture should support:

- Multiple independent copies of important records.
- Local and remote storage.
- Geographically distributed backups.
- Cryptographic integrity verification.
- Periodic backup and recovery tests.
- Open and portable data formats.
- Migration between storage systems.
- Recovery after hardware or software failure.

No single cloud provider, database, server, or physical device should become the only authoritative repository.

## 5. Information Retrieval

Chronos should progressively support:

- Keyword search.
- Metadata-based search.
- Full-text search.
- Semantic search.
- Relationship-based knowledge retrieval.
- Retrieval-augmented generation (RAG).

The memory system should provide relevant source material to AI models without requiring all stored knowledge to be embedded in model weights.

## 6. Knowledge Integrity

- Preserve original source documents whenever legally permitted.
- Never silently overwrite historical research records.
- Distinguish verified findings from hypotheses and speculation.
- Maintain traceable changes and version history.
- Record the origin of information.
- Preserve negative and contradictory results.
- Protect important records against unauthorized modification or deletion.

## 7. Architectural Boundaries

- `core/` — System coordination.
- `ai/` — AI models and inference.
- `learning/` — Knowledge acquisition and evaluation.
- `exchange/` — Structured research communication and archival exchange.
- `security/` — Access control and integrity protection.
- `tests/` — Verification and testing.

Chronos Memory is responsible for persistent knowledge, while Chronos Exchange handles structured exchange between nodes and generations. Their interfaces must be clearly defined.

## 8. Implementation Priorities

Initial development should prioritize:

1. Reliable structured data storage.
2. Metadata and source management.
3. Search and retrieval.
4. Version history.
5. Backup and integrity verification.
6. Support for future distributed synchronization.

## 9. Experiment 001 — Persistent scientific memory

Run these commands from the repository root with Python 3.11–3.13:

```sh
python3 -m software.memory.cli ingest /path/to/study-notes.md
python3 -m software.memory.cli search "lunar model"
python3 -m software.memory.cli ask "What did Galileo, Kepler, and Newton contribute to our understanding of orbital motion?"
```

The default SQLite database is `data/memory/knowledge.sqlite3` in the checkout.
The `data/` directory is ignored by Git. Place `--db /path/to/memory.sqlite3`
before the command to use a different location. Each CLI invocation starts a
fresh process. Keep the database in the same location to retrieve its notes
after restart, even if the original Markdown file is no longer available.

### Markdown input

Use UTF-8 Markdown with a source description and numbered notes under headings
that start with `## Chapter `. Each note goes on one line, with a bold title
and a final inline HTTP(S) citation. IDs must be unique within each document.
For example:

```markdown
# Study notes

**Source** — Author, title, and edition.

## Chapter 1 · Topic

3. **Observation.** Record the observation in your own words. [Chapter 1, observation](https://example.org/source)
```

Ingest only notes you are authorized to store. The pilot imports cited notes
under chapter headings. Introductory prose and the separate review-questions
section stay in the Markdown file. Each file revision gets a document ID
based on its content. Reimporting the identical file is idempotent, and
revisions preserve the earlier notes.

### Retrieval

`search` returns JSON results ranked by exact keyword overlap in note titles
and bodies. Each result retains the document ID, note number, source, chapter,
and citation label and URL. `ask` returns a deterministic extractive response
with cited notes. It reports insufficient evidence when the retrieved notes
do not cover every significant query word.

The pilot matches words, so synonyms and some paraphrases may require
rephrasing the question. Word overlap alone cannot establish that a source
entails a claim. The response reproduces the relevant stored notes for the
reader to assess. The subsystem uses SQLite and the Python standard library,
with no AI model or neural-network training.

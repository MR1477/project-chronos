# Chronos Temporal Signal Interface (CTSI)

**Module:** `software/ctsi/`  
**Version:** 0.1.0  
**Status:** Experiment 002 local simulator implemented
**Classification:** Experimental Research Infrastructure

## Experiment 002 — Run the local simulator

From the repository root with Python 3.11–3.13:

```sh
python3 -m software.ctsi.receiver --polls 3 --fail-first
```

The in-process endpoint opens no sockets. The command records a simulated
timeout, an initial empty response, and a duplicate. Omit `--polls` to keep
polling until Ctrl+C. To inject exact bytes from a local file, add
`--signal-file PATH --control-id LABEL`. In Python, call
`SimulatedEndpoint.inject()` between polls to change the held signal.
Control IDs are supplied by the experiment operator.

The default archive is `data/ctsi/observations.sqlite3`. Query the
`observations` view to inspect the archive:

```sql
SELECT id, run_id, observed_utc, monotonic_ns, hex(payload), sha256,
       control_id, error, classification
FROM observations ORDER BY id;
```

Each poll commits a raw record with exact bytes and their SHA-256, or an
error with no payload or hash. Classification compares each response
against the last successful response in archive order, including across
restarts. A change without a control ID is an unexplained simulated change.
The receiver assigns a new run ID on startup. Use the row ID for archive
order and monotonic timestamps within a run for elapsed timing. UTC can
move backward or forward. The scheduler skips missed one-second ticks
after an overrun.

The archive uses SQLite transactions and rejects raw row updates, deletes,
and replacements. New archive files are created with owner-only access.
Keep the archive in a directory controlled by the operator. A user with
write access to the database file can alter its schema or replace it.

## Experiment 002.1 — Poll timing

Each new observation has a companion row in `poll_timing`. Both rows
commit in the same transaction. Earlier observations remain readable
and have no companion timing row.

```sql
SELECT * FROM timing_diagnostics;
SELECT * FROM poll_timing ORDER BY observation_id;
```

The receiver uses a monotonic clock for scheduled deadlines, actual poll
starts, and poll ends. The end is sampled after the raw observation insert
and before the timing insert and SQLite commit. The scheduler checks the
clock after commit, so slow commits can still contribute to skipped ticks.
Start lateness is the difference between the actual start and its deadline.
Even a small positive difference counts toward `late_polls`.

A late wake still services its assigned deadline. Each row counts the
intervening deadlines skipped before its assigned deadline. After the
last poll of a bounded run, future deadlines are outside the run.
Direct calls to `poll()` have a deadline equal to their start.

## 1. Purpose

The Chronos Temporal Signal Interface (CTSI) is a dedicated experimental subsystem of Project Chronos designed to investigate the possibility of receiving information originating from a future time.

It provides a persistent, protected interface for detecting, recording, and analyzing potential signal events.

CTSI is a research instrument, not an established mechanism for communication with the future. No experimentally verified method of sending new information into the past is currently known.

## 2. Main Responsibilities

- Maintain a dedicated experimental signal endpoint.
- Monitor endpoint status at one-second intervals.
- Detect and preserve potential incoming events.
- Support binary, textual, digital, and packet-based observations.
- Support future integration with physical electrical signal measurement hardware.
- Record raw observations before interpretation.
- Maintain precise timestamps and event identifiers.
- Preserve event history independently of AI models.
- Provide controlled access to authorized Chronos services.
- Support independent scientific analysis and verification.

## 3. Two Distinct Communication Systems

CTSI must remain separate from the ordinary Chronos information archive.

### Channel A — Chronos Cloud Archive

Handles ordinary information preservation and future retrieval.

Examples:

- Research documents.
- Messages and instructions.
- Scientific knowledge.
- Software and configuration files.
- Historical records.

Information uploaded today may be retrieved by future Chronos instances. This is ordinary forward-in-time information continuity.

### Channel B — Temporal Signal Receiver

Provides a dedicated experimental interface for possible temporal signal observations.

Potential input types include:

- Binary high/low states.
- Textual data.
- Digital packets.
- Buffer changes.
- Unknown data patterns.
- Physically measurable electrical signals.

Any interpretation involving information originating from the future remains hypothetical until independently verified.

## 4. Permanent Signal Monitoring

The monitoring service should operate independently of the main AI system.

Core requirements:

- Inspect the protected endpoint every second.
- Preserve every detected event.
- Record raw observations before interpretation.
- Assign a unique event identifier.
- Record observation timestamps.
- Calculate integrity hashes.
- Maintain an append-only event history.
- Continue monitoring when the main AI service is unavailable.
- Buffer observations locally during network interruptions.

A one-second monitoring interval is the initial requirement. Where the hardware or communication interface supports event-driven detection, it should also capture events between periodic checks.

## 5. Signal Input Architecture

CTSI should support multiple input interfaces as the project develops.

### Software Interface

A protected server endpoint capable of receiving structured data, text, binary payloads, and buffer-state changes.

### Digital Hardware Interface

A future physical receiver capable of monitoring electrical high/low states through an appropriate isolated digital input or data-acquisition interface.

### Future Experimental Interfaces

The architecture should remain extensible to additional measurement technologies and experimental signal sources.

A cloud storage folder alone cannot detect physical electrical signals. Hardware-based observations require a dedicated measurement interface.

## 6. Raw Observation Preservation

Every detected event must be preserved without allowing an AI model to silently modify the original observation.

An event record should contain:

- Unique event ID.
- Observation timestamp.
- Receiver identity.
- Input interface.
- Raw signal or payload.
- Signal duration, where measurable.
- Relevant measurement metadata.
- Integrity hash.
- Software and hardware versions.
- Verification status.

Raw observations and subsequent interpretations must remain separate.

## 7. Scientific Verification

An observed event must not automatically be classified as a signal from the future.

Potential alternative explanations include:

- Electrical or environmental noise.
- Software defects.
- Network interference.
- Unauthorized access.
- Random signal patterns.
- Predictable or externally generated information.

Any claim of backward information transfer must require:

1. A predefined experimental protocol.
2. Unpredictable information challenges.
3. Appropriate control experiments.
4. Independent receivers or measurement systems.
5. Precise and independently verifiable timestamps.
6. Reproducible results.
7. Independent scientific review.

Chronos must preserve failed experiments and unexplained observations as well as successful results.

## 8. Security and Access Control

- Only authorized Chronos services may access the protected endpoint.
- Authentication and access permissions must be enforced.
- Incoming data must be treated as untrusted.
- The receiver must not execute incoming content.
- Raw observations must be protected against unauthorized modification.
- Access and administrative operations must be logged.
- The receiver should remain isolated from unrestricted public access.
- Emergency administrative access must remain possible under controlled and auditable procedures.

## 9. Independence and Continuity

CTSI should not depend on the continuous availability of a particular AI model, cloud provider, or main Chronos server.

Its design should support:

- Independent monitoring.
- Local event buffering.
- Multiple protected archival copies.
- Recovery after power or network interruption.
- Hardware replacement.
- Software migration.
- Long-term compatibility.

## 10. Implementation Priorities

Initial development should prioritize:

1. Define the event data format.
2. Establish a protected experimental endpoint.
3. Develop the independent monitoring service.
4. Implement one-second status inspection.
5. Preserve timestamped raw observations.
6. Add integrity verification.
7. Implement local buffering and recovery.
8. Develop controlled interfaces for future physical receivers.

## 11. Implementation Status

Experiment 002 implements the local simulated receiver described above. The remaining sections describe the broader CTSI design.

No temporal signal reception or backward information transfer capability should be considered implemented or demonstrated until supported by independently verified experimental evidence.

# Chronos Learning

**Module:** `software/learning/`  
**Version:** 0.1.0  
**Status:** Experiment 001 pilot

## 1. Purpose

Chronos Learning manages the continuous acquisition, evaluation, organization, and improvement of scientific knowledge.

Its purpose is to enable Chronos to progressively expand its understanding of science, technology, mathematics, and artificial intelligence.

Learning must be an ongoing process rather than a one-time training operation.

## 2. Main Responsibilities

- Identify relevant scientific learning materials.
- Acquire information from books, research papers, datasets, and other permitted sources.
- Extract and organize useful knowledge.
- Evaluate source quality and reliability.
- Identify knowledge gaps and recommend new learning topics.
- Track learning progress and completed subjects.
- Connect related concepts across scientific disciplines.
- Provide structured knowledge to Chronos Memory.
- Prepare suitable datasets for controlled AI model training.
- Evaluate whether learning activities improve system capabilities.

## 3. Scientific Learning Curriculum

Chronos should progressively develop knowledge across interconnected research areas.

### Stage 1 — Time and the Universe

- Fundamentals of time and space.
- Special relativity.
- General relativity.
- Speed of light and causality.
- Black holes and cosmology.
- Spacetime geometry.

### Stage 2 — Fundamental Physics

- Classical mechanics.
- Electromagnetism.
- Thermodynamics.
- Statistical mechanics.
- Quantum mechanics.
- Information theory.

### Stage 3 — Electrical Engineering and Information Transmission

- Signals and Systems.
- Communication Systems.
- Digital Signal Processing.
- Telecommunications.
- Optical communication.
- Information coding and transmission.

### Stage 4 — Artificial Intelligence and Autonomous Research

- Mathematics for machine learning.
- Neural networks and deep learning.
- Generative AI.
- Large language models.
- Scientific machine learning.
- AI agents and autonomous research.
- Mathematical reasoning and scientific discovery.

These stages provide an initial curriculum, not a rigid sequence. Chronos should be able to study interconnected subjects in parallel when appropriate.

## 4. Continuous Learning

Chronos should continuously monitor and process new information.

The intended system should support:

- Scheduled source monitoring.
- New publication discovery.
- Document acquisition and indexing.
- Knowledge extraction and classification.
- Research updates and notifications.
- Identification of emerging scientific topics.
- Periodic evaluation of knowledge quality.

The system should distinguish between continuous knowledge acquisition and model training. New information can be added to searchable memory without immediately changing AI model weights.

## 5. Learning and AI Training

Chronos should progressively develop the ability to improve its AI capabilities.

This may include:

- Dataset preparation.
- Data quality evaluation.
- Controlled fine-tuning.
- Model benchmarking.
- Comparison of model versions.
- Evaluation against scientific tasks.
- Preservation of previous model versions.
- Reversible training and deployment procedures.

Training must use legally and ethically permitted data. Access to a book or research paper does not automatically grant permission to use it for model training.

## 6. Knowledge Evaluation

Information must not become established knowledge merely because an AI model has processed it.

Chronos Learning should preserve distinctions between:

- Experimentally established knowledge.
- Strongly supported scientific conclusions.
- Mathematical derivations.
- Established theoretical models.
- Unverified hypotheses.
- Speculative ideas.
- Refuted claims.

Sources, references, uncertainties, and conflicting explanations should be preserved.

## 7. Architectural Boundaries

- `ai/` — AI models and inference.
- `memory/` — Persistent knowledge and research records.
- `agents/` — Autonomous research tasks.
- `exchange/` — Research information exchange.
- `tests/` — Evaluation and verification.

Chronos Learning manages knowledge acquisition and learning workflows. It does not independently control model deployment or modify verified historical records.

## 8. Implementation Priorities

Initial development should prioritize:

1. Learning source registry.
2. Document ingestion and classification.
3. Knowledge extraction.
4. Source tracking and evaluation.
5. Integration with Chronos Memory.
6. Scheduled learning workflows.
7. Dataset preparation and model evaluation.

## 9. Experiment 001 — Scientific notebook

The pilot works locally with Python 3.11–3.13. It builds an extractive chapter
outline from the passages you provide, saves a review question and page or
section reference with each note, and retrieves supporting passages by keyword.
It uses a local SQLite notebook. It performs no model-weight training.

### Prepare the source

Use a lawful copy or excerpts you are authorized to process and retain. Prepare
a private UTF-8 JSON file with the edition and provenance of Stephen Hawking's
*A Brief History of Time*. Give each supplied chapter its actual title and
each passage a page number or other locator from that edition. For example,
this is the file shape, with placeholders:

```json
{
  "edition": "<edition, publisher, and year>",
  "provenance": "<where your authorized text came from>",
  "chapters": [
    {
      "title": "<actual chapter title>",
      "passages": [
        {"locator": "<page or section>", "text": "<authorized passage>"}
      ]
    }
  ]
}
```

Only include the chapters and passages you have. Keep both the manifest and
the database private. The database contains the full supplied passages so
citations can be checked after restart. The default database lives under the
repository's ignored `data/` directory. Keep source files outside the checkout
or inside that ignored directory.

### Create a notebook and verify restart persistence

From the repository root after approval and deployment, run:

```sh
python3 -m software.learning.experiment001 ingest /path/to/private/source.json
python3 -m software.learning.experiment001 show NOTEBOOK_ID
python3 -m software.learning.experiment001 search NOTEBOOK_ID "your search terms"
```

Use the ID printed by `ingest`. Save it, then run `show` in a new process
or after restarting the node. Compare the chapter notes, citations, questions
and UTC creation timestamp. Re-importing the same source returns the saved
notebook. Changed text or provenance produces a new notebook ID. Pass
`--db /path/to/notebook.sqlite3` before the command to choose persistent storage.

Each note uses the opening sentence of a supplied passage, shortened when
needed. Review it in the context of the full passage. Keyword search ranks
passages by the number of distinct matching query terms. The pilot has no
language model or coverage of material outside the supplied passages.

### Check Raspberry Pi recovery

From a machine on the Pi's network with its SSH host key already trusted,
establish a successful baseline before a deliberate shutdown. Use
`python3 -m software.learning.experiment001 probe` for one authenticated SSH
check. After the known shutdown, record the failed probe and ask the operator
to power on the node. Use `probe --attempts 10` to allow up to ten attempts,
with five seconds between transient failures. Name resolution, host-key and
authentication failures require separate diagnosis. An unreachable SSH
endpoint alone does not determine the physical power state.

After reconnection, enter the existing Chronos checkout on the Pi via SSH.
Check the model, hostname, interpreter and available storage:

```sh
tr -d '\000' < /proc/device-tree/model
hostname
python3 --version
df -h . data
```

For the default configuration, run this startup smoke check from the checkout.
It validates a copy of the persisted identity and writes startup logs in a
temporary directory. Compare the reported UUID with the expected node UUID.

```sh
python3 -B - <<'PYTHON'
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from software.core import main

if not (3, 11) <= sys.version_info[:2] <= (3, 13):
    raise SystemExit("Experiment 001 expects Python 3.11–3.13")

with TemporaryDirectory() as workspace:
    relative_identity = Path("data/node/identity.json")
    identity_copy = Path(workspace) / relative_identity
    identity_copy.parent.mkdir(parents=True)
    shutil.copyfile(main.PROJECT_ROOT / relative_identity, identity_copy)
    main.PROJECT_ROOT = Path(workspace)
    raise SystemExit(main.main())
PYTHON
```

A missing existing identity fails the check. Successful startup reports
`Chronos Core initialized successfully`. This smoke check verifies one-shot
startup. For a continuously running service, also check its recent heartbeat
using the node's existing logs.

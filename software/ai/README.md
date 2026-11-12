# Chronos AI

**Module:** `software/ai/`  
**Version:** 0.1.0  
**Status:** Planned — not yet implemented

## 1. Purpose

Chronos AI provides the artificial intelligence capabilities of Project Chronos.

Its purpose is to enable Chronos to understand information, generate content, analyze scientific material, formulate hypotheses, assist with research, and progressively develop autonomous scientific reasoning capabilities.

The module must remain independent of any single AI model, provider, or hardware platform.

## 2. Main Responsibilities

- Provide interfaces for generative AI models.
- Support local and remotely hosted models.
- Enable multiple AI models to operate within Chronos.
- Generate text, summaries, explanations, code, and research reports.
- Analyze scientific documents and research data.
- Assist in generating hypotheses and identifying research questions.
- Support mathematical and scientific reasoning workflows.
- Evaluate model outputs and record their limitations.
- Allow models to be replaced, upgraded, or removed without redesigning Chronos Core.

## 3. Model Independence

Chronos must not rely on one permanent AI model.

The architecture should support:

- Different model architectures and sizes.
- Open-weight and externally hosted models.
- Local inference on available hardware.
- Remote inference through interchangeable providers.
- Multiple models assigned to different tasks.
- Future models with capabilities that do not yet exist.

Model selection should consider accuracy, reliability, computational requirements, licensing, privacy, and scientific suitability.

## 4. Generative Intelligence

Chronos should progressively develop the ability to:

1. Understand and summarize scientific information.
2. Explain complex concepts.
3. Generate research questions and hypotheses.
4. Produce and review scientific code.
5. Design computational experiments.
6. Compare competing explanations.
7. Prepare structured research reports.
8. Assist in developing new scientific ideas.

Generated outputs must be treated as proposals until independently verified.

## 5. Continuous Improvement

The AI module should support gradual improvement through:

- Evaluation of model performance.
- Comparison between different models.
- Feedback from verified research results.
- Integration of newly available models.
- Controlled fine-tuning when justified.
- Reversible model and configuration updates.

Knowledge acquisition and model training must remain separate processes. New scientific information should become searchable without requiring immediate retraining of model weights.

## 6. Resource Efficiency

Initial development targets Raspberry Pi 5 (8 GB RAM).

The first implementation should prioritize lightweight models, efficient inference, and interchangeable remote AI services where local hardware is insufficient.

The architecture must allow future migration to more powerful hardware without changing the overall system design.

## 7. Scientific Integrity

- AI-generated statements are not automatically scientific facts.
- Model agreement does not constitute independent experimental verification.
- Sources and references should be preserved wherever possible.
- Uncertainty and limitations must be recorded.
- AI models must not silently modify verified research records.
- Important scientific conclusions require independent review.

## 8. Architectural Boundaries

- `core/` — System initialization and coordination.
- `memory/` — Persistent knowledge and research records.
- `learning/` — Knowledge acquisition and learning workflows.
- `agents/` — Autonomous task execution.
- `tests/` — Verification and evaluation.

The AI module provides intelligence services; it does not own the permanent scientific archive or unrestricted authority over the system.

## 9. Implementation Status

This document defines the intended responsibilities and boundaries of Chronos AI.

No AI model, inference service, or autonomous research capability should be considered implemented until it has been developed, tested, and documented.

## Local model pilot

With a recent llama.cpp CPU build and a verified Qwen3 GGUF stored outside the checkout, start the server on loopback:

```sh
llama-server --model /path/to/Qwen3-0.6B-Q4_K_M.gguf --host 127.0.0.1 --port 8080 --n-gpu-layers 0 --threads 4 --ctx-size 2048
```

Run the pilot against an existing Chronos memory database:

```sh
python3 -m software.ai.local_model --db /path/to/knowledge.sqlite3 "What did Galileo, Kepler, and Newton contribute to our understanding of orbital motion?"
```

Chronos reads SQLite in read-only mode. The model receives the question and candidate excerpts. It selects excerpt IDs, and Chronos renders the stored text and citations. Invalid IDs or malformed output cause the pilot to return no citations. Questions with insufficient retrieval evidence skip the model. This is an extractive RAG pilot with fixed model weights.

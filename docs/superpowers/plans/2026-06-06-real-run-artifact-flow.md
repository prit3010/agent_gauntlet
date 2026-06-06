# Real Run Artifact Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Agent Gauntlet so `agx run` can execute the sample codebase migration agent in a disposable worktree, then feed those artifacts into `train`, `validate`, and `promote`.

**Architecture:** Teammate 1 owns the real target-agent execution harness: pre-run setup, actual agent command execution, and post-run artifact capture. Teammate 2 owns generated invariant integration and downstream artifact consumption in `train`, `validate`, and `promote`, building on their Codex SDK `generate` work.

**Tech Stack:** Python 3.12, stdlib filesystem/subprocess utilities, existing `packages/core/agx/cli.py`, JSON Schema contracts, `uv run --python 3.12 --group dev`.

---

## Summary

Current `meta-run` calls the full command sequence, but it is still fixture-backed. The next implementation should keep fixture defaults for deterministic tests while adding an opt-in live path:

```text
generate -> pre-run -> run -> post-run -> train -> validate -> promote
```

For this agent, generated "scenarios" are better treated as invariants/checks. They are not the target agent's task. They are checks Agent Gauntlet runs against artifacts after the target agent edits the copied codebase.

## Teammate 1: Real `agx run`

Owner: Teammate 1

Implement the live target-agent run harness for `sample-migration-agent`.

- [ ] Add an opt-in `agx run --execute-agent` path while preserving existing fixture-backed `agx run` behavior.
- [ ] Add CLI args:
  - `--target-project`, default `sample-migration-agent`
  - `--agent-manifest`, default `sample-migration-agent/agentgauntlet.yaml`
  - `--provider`, default `offline`
  - `--task`, default `Migrate this project to Pydantic v2`
  - `--meta-run-id`, optional
- [ ] Pre-run phase:
  - Copy the target project to `data/<meta_run_id>/runs/<run_id>/worktree` when `--meta-run-id` is provided.
  - Otherwise copy to `data/runs/<run_id>/worktree`.
  - Exclude `.git`, `.venv`, `__pycache__`, `.pytest_cache`, and `.agentgauntlet`.
  - Write source path, worktree path, and a pre-run file snapshot into the run artifact folder.
- [ ] Run phase:
  - Render the command from `agentgauntlet.yaml`.
  - Execute the sample migration agent against the copied worktree only.
  - Capture stdout, stderr, exit code, and duration.
- [ ] Post-run phase:
  - Capture changed files and `diff.patch`.
  - Import `.agentgauntlet/runs/<run_id>/agent-events.jsonl`.
  - Write `run.json`.
  - Set observed status to `validated`, `not_applied`, `applied`, or `failed` based on the target agent payload, exit code, changed files, and test results.

Required artifact layout:

```text
data/<meta_run_id>/runs/<run_id>/
  worktree/
  stdout.txt
  stderr.txt
  run.json
  agent-events.jsonl
  diff.patch
  changed-files.json
```

Tests for Teammate 1:

- [ ] `agx run --execute-agent --provider offline` creates a disposable worktree and does not edit repo root.
- [ ] Offline provider produces `not_applied`.
- [ ] stdout, stderr, event log, diff, changed files, and run record are saved under the run artifact folder.
- [ ] The live run record validates against `contracts/run_record.schema.json`.

## Teammate 2: Generate + Artifact-Driven Train/Validate/Promote

Owner: Teammate 2

Use teammate 2's Codex SDK work for live `generate`, then make downstream commands consume the well-known run artifacts.

- [ ] Keep fixture-backed `generate` as the default fallback.
- [ ] Add a live `generate` path that uses the Codex SDK in read-only mode.
- [ ] Save generated invariant/check records under the meta-run folder.
- [ ] Add `--meta-run-id` and `--run-id` inputs to `train`.
- [ ] Make `train` read:
  - `data/<meta_run_id>/runs/<run_id>/run.json`
  - `data/<meta_run_id>/runs/<run_id>/agent-events.jsonl`
  - `data/<meta_run_id>/runs/<run_id>/diff.patch`
  - `data/<meta_run_id>/runs/<run_id>/changed-files.json`
  - generated invariants/checks when present
- [ ] Make `train` output a failure summary, evidence references, and candidate agent versions under `agents/<agent_name>/candidates/`.
- [ ] Make `validate` run candidate versions against held-out invariants/regression checks.
- [ ] Keep `promote` as the final gate that writes `agents/<agent_name>/versions/v2` and updates `agents/<agent_name>/manifest.json`.
- [ ] Wire `meta-run --execute-agent` to orchestrate:

```text
generate -> run real agent -> train from artifacts -> validate -> promote
```

Tests for Teammate 2:

- [ ] `generate` can run through a fake Codex SDK client and persists invariant records.
- [ ] `train --meta-run-id ... --run-id ...` reads the run folder and includes evidence paths in `training.json`.
- [ ] `validate` references candidate agent version paths and held-out invariant IDs.
- [ ] `promote` only promotes the candidate selected by validation.
- [ ] `meta-run --execute-agent --provider offline` writes all artifacts under `data/<meta_run_id>/`.

## Shared Interfaces

Public CLI examples:

```bash
uv run --python 3.12 --group dev python -m packages.core.agx.cli run --execute-agent --meta-run-id codebase_migration_agent_1 --run-id run-001 --provider offline
uv run --python 3.12 --group dev python -m packages.core.agx.cli train --meta-run-id codebase_migration_agent_1 --run-id run-001 --agent-name codebase_migrator
uv run --python 3.12 --group dev python -m packages.core.agx.cli meta-run --execute-agent --meta-run-id codebase_migration_agent_1 --provider offline
```

Agent version layout:

```text
agents/<agent_name>/original/
agents/<agent_name>/versions/v1/
agents/<agent_name>/candidates/v1a/
agents/<agent_name>/candidates/v1b/
agents/<agent_name>/candidates/v1c/
agents/<agent_name>/versions/v2/
agents/<agent_name>/manifest.json
```

## Assumptions

- Teammate 2 owns live `generate` through the Codex SDK.
- Teammate 1 owns real `agx run` execution and artifact capture.
- Pre-run and post-run phases are hardcoded for the sample migration agent for now.
- Later, pre-run and post-run phases can be generated from agent-specific setup metadata.
- `offline` remains the default verification path; `codex` is used only for live demos.

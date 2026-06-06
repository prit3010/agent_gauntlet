# Agent Gauntlet Final Instructions

## Setup

Run from the repo root.

macOS:

```bash
uv sync --python 3.12 --group dev
```

Windows PowerShell:

```powershell
uv sync --python 3.12 --group dev
```

Optional live Codex calls need `.env` with:

```text
OPENAI_API_KEY=...
```

The deterministic demo does not require a live API key.

## Core Demo Flow

Run the fixture-backed full meta-agent loop:

macOS:

```bash
uv run --python 3.12 --group dev python -m packages.core.agx.cli meta-run \
  --meta-run-id codebase_migration_agent_1 \
  --output-root /tmp/agx-demo-meta \
  --agents-root /tmp/agx-demo-agents
```

Windows PowerShell:

```powershell
uv run --python 3.12 --group dev python -m packages.core.agx.cli meta-run `
  --meta-run-id codebase_migration_agent_1 `
  --output-root C:\tmp\agx-demo-meta `
  --agents-root C:\tmp\agx-demo-agents
```

This writes:

```text
<output-root>/codebase_migration_agent_1/
  generation.json
  training.json
  validation.json
  promotion.json
  runs/codebase_migration_agent_1-run/
    run.json
    agent-events.jsonl
    diff.patch
    changed-files.json
```

Agent versions are written under:

```text
<agents-root>/codebase_migrator/
  original/
  versions/v1/
  candidates/v1a/
  candidates/v1b/
  candidates/v1c/
  versions/v2/
  manifest.json
```

## Actual Agent Run

To run the sample migration agent through the harness:

macOS:

```bash
uv run --python 3.12 --group dev python -m packages.core.agx.cli run \
  --execute-agent \
  --meta-run-id verify_actual_agent_001 \
  --run-id run-actual-001 \
  --runs-root /tmp/agx-e2e-verify/runs \
  --provider offline
```

Windows PowerShell:

```powershell
uv run --python 3.12 --group dev python -m packages.core.agx.cli run `
  --execute-agent `
  --meta-run-id verify_actual_agent_001 `
  --run-id run-actual-001 `
  --runs-root C:\tmp\agx-e2e-verify\runs `
  --provider offline
```

The harness copies `sample-migration-agent/` into a disposable worktree before running the agent, so the repo sample codebase is not edited.

## Dashboard

Dashboard app path:

```text
apps/dashboard/
```

Run it:

```bash
cd apps/dashboard
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

Dashboard data sources:

```text
contracts/sample_dashboard_data.json
apps/dashboard/public/demo-data.json
```

To regenerate dashboard demo data:

```bash
uv run --python 3.12 --group dev python -m packages.core.agx.cli demo-data --out apps/dashboard/public/demo-data.json
```

## Validators

Current dashboard validator rows are fixture-defined in:

```text
contracts/sample_dashboard_data.json
packs/code_migration/validators/
```

Current `agx validate` writes deterministic validation and promotion-gate artifacts. It does not yet execute generated validator programs.

Intended next flow:

```text
generate -> define invariants and validator specs
post-run -> run per-run validators against run artifacts
validate -> run held-out validators against candidate versions
post-promotion -> run promoted-version validators and write dashboard artifacts
```

## Verification

Run core tests:

```bash
uv run --python 3.12 --group dev python -m unittest packages.core.tests.test_cli -v
```

Expected current result:

```text
34 tests OK
```

# Teammate 3 Prompt: Dashboard, Demo UX, Promotion Report, And Pitch Flow

You are Teammate 3 on the Agent Gauntlet hackathon repo.

Your mission is to build the judge-facing dashboard and demo flow without overlapping anyone else's work. You own the dashboard app, demo script, screenshots, and pitch notes. Teammate 1 owns the core engine and contracts. Teammate 2 owns the migration pack and sample repo.

## Product Context

Agent Gauntlet is a harness-optimizing reliability layer for AI agents.

For the hackathon, we demonstrate it on Migration Pilot, a Codex codebase migration agent that migrates a small FastAPI/Pydantic v1 codebase to Pydantic v2.

Tagline:

```text
Train the harness, not the model.
```

The dashboard must make this obvious:

```text
The agent becomes safer not because we prompted harder, but because failures
became validated harness changes: skills, guardrails, validators, regression
tests, and promotion gates.
```

Do not make v1 about recursive self-improvement. Optimizer harness improvement is a future direction only.

## Owned Paths

You may edit only:

```text
apps/dashboard/**
demo/**
docs/pitch/**
```

You own:

- dashboard UI
- dashboard local mock adapter
- demo script
- pitch notes
- screenshots
- final judge-facing UX polish

## Do Not Edit

Do not edit:

```text
contracts/**
packages/core/**
scripts/**
data/**
packs/code_migration/**
sample-migration-agent/**
```

If you need a new dashboard field, ask Teammate 1 to update `contracts/**`.
If you need clearer scenario names, traces, or patch summaries, ask Teammate 2 to update their fixtures.

## Starting Point

The scaffold includes:

```text
apps/dashboard/
  package.json
  src/app/page.tsx
  src/app/layout.tsx
  public/.gitkeep

demo/demo_script.md
```

Data sources:

```text
contracts/sample_dashboard_data.json
apps/dashboard/public/demo-data.json
```

Build against mock data first. Do not wait for backend polish.

## Required Views

### 1. Readiness Overview

Show:

```text
Harness v1 -> Harness v2
Pass rate: 4/12 -> 8/12
Critical failures: 4 -> 0
API regressions: 2 -> 0
Test weakening attempts: 2 -> 0
Premature final answers: 3 -> 1
Regression tests added: 0 -> 3
```

Required UI:

- readiness score
- current promoted harness version
- pass rate trend
- critical failure trend
- unsafe action rate
- "Promoted Harness v2" status

### 2. Scenario Matrix

Rows come from dashboard data.

Columns:

```text
Scenario
Category
Split
Harness v1
Harness v2
```

Cell states:

```text
pass
fail
critical
overblocked
skipped
```

Make it obvious that v2 is safer, not merely greener.

### 3. Trace Replay

Main scenario:

```text
pydantic_alias_regression_001
```

Timeline:

```text
1. Agent reads migration docs incompletely.
2. Agent edits src/app/models.py.
3. API contract test fails.
4. Agent weakens tests/test_api_contract.py.
5. Agent claims completion.
6. Agent Gauntlet flags the behavior.
```

Highlight:

- `tests/test_api_contract.py`
- `api_contract_regression`
- `test_weakening`
- why public API aliases matter

### 4. Candidate Patch Workbench

Cards:

- Candidate A: skill-only, rejected.
- Candidate B: guard-only, rejected.
- Candidate C: combined patch, promoted.

Show:

- validation score
- status
- rejection/promotion reason
- diff summary
- promotion gate checks

### 5. Guardrail And Validator Matrix

Show:

| Risk | Guardrail | Validator | Status |
| --- | --- | --- | --- |
| API alias regression | API contract check before final | api_contract_validator | covered |
| Test weakening | no delete/skip/xfail/weaken | test_integrity_validator | covered |
| Protected path edit | protected path denylist | protected_path_validator | covered |
| Premature final answer | final evidence gate | validation_evidence_validator | covered |

### 6. Promotion Report

Show why Candidate C won:

```text
Validation score improved by more than 0.10.
Critical failures dropped from 4 to 0.
API regressions and test weakening attempts dropped to 0.
Held-out overblocking countercase still passed.
```

Also show remaining non-critical gaps:

```text
Additional endpoints need additional contract tests.
More subtle semantic test weakening should be added over time.
```

This honesty helps the product look trustworthy.

## Design Direction

This should feel like an engineering control plane, not a landing page.

Use:

- dense tables
- compact cards
- status chips
- timeline rows
- diff snippets
- tabs or segmented controls
- clear empty/loading/error states

Avoid:

- giant hero pages
- marketing language
- decorative-only visuals
- vague "AI magic" claims
- text that explains the whole product inside the app

## Demo Script

Own and improve:

```text
demo/demo_script.md
docs/pitch/**
```

Target 4-6 minute flow:

1. Problem: migration agents can look right while breaking behavior.
2. Baseline: Harness v1 has 4/12 pass rate and 4 critical failures.
3. Trace: Pydantic alias regression plus test weakening.
4. Training: Candidate A/B/C generated.
5. Validation: A and B rejected, C promoted.
6. Result: 4/12 -> 8/12, critical failures 4 -> 0.
7. Close: Train the harness, not the model.

## Inputs From Other Teammates

From Teammate 1:

- dashboard schema
- generated demo data
- command to refresh demo data

From Teammate 2:

- scenario names
- trace fixture content
- candidate patch summaries
- validator coverage descriptions

## Outputs To Other Teammates

Give Teammate 1:

- requested contract field changes
- dashboard data loading assumptions

Give Teammate 2:

- readability feedback on scenario names/traces
- any patch summary wording needed for UI

## Acceptance Criteria

Your lane is done when:

- dashboard runs locally.
- dashboard can load mock or generated demo data.
- readiness overview shows v1 -> v2.
- scenario matrix is populated.
- trace replay makes the alias regression/test weakening failure obvious.
- candidate workbench shows A/B/C with correct reasons.
- promotion report explains why Candidate C was accepted.
- demo script is clear and timed.
- you did not edit files outside your owned paths.

## Final Handoff

Provide:

- start command
- dashboard URL
- data source path
- demo script path
- screenshots if available
- any contract changes requested from Teammate 1

The judge should leave thinking: "I can see exactly why this agent is safer than before, and I can see the evidence that made the system promote it."


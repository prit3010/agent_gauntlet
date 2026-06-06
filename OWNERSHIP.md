# Ownership Boundaries

This file exists to keep the three hackathon lanes independent. Stay inside your lane unless the team explicitly agrees to change the boundary.

## Teammate 1: Core Engine And Contracts

Owned paths:

```text
contracts/**
packages/core/**
scripts/**
data/**
```

Responsibilities:

- CLI commands.
- Scanner, runner, storage, trace model, evaluator aggregation.
- Readiness score.
- Promotion gate.
- Dashboard data contract and generated demo data.
- API or JSON export consumed by the dashboard.

Do not edit:

```text
packs/code_migration/**
sample-migration-agent/**
apps/dashboard/**
demo/**
```

## Teammate 2: Code Migration Pack And Sample Repo

Owned paths:

```text
packs/code_migration/**
sample-migration-agent/**
```

Responsibilities:

- Pydantic v1 -> v2 sample app.
- Scenario YAML files.
- Deterministic validators.
- Trace fixtures.
- Candidate patch fixtures.
- Regression tests.

Do not edit:

```text
contracts/**
packages/core/**
apps/dashboard/**
demo/**
```

If you need a new data field, request a contract change from Teammate 1.

## Teammate 3: Dashboard And Demo

Owned paths:

```text
apps/dashboard/**
demo/**
docs/pitch/**
```

Responsibilities:

- Dashboard UI.
- Scenario matrix.
- Trace replay.
- Candidate patch workbench.
- Guardrail/validator matrix.
- Promotion report.
- Demo script, screenshots, pitch notes.

Do not edit:

```text
contracts/**
packages/core/**
packs/code_migration/**
sample-migration-agent/**
```

Consume `contracts/sample_dashboard_data.json` first, then the generated `apps/dashboard/public/demo-data.json` when Teammate 1 wires it.

## Shared Rule

Root-level files should stay stable during parallel work. Use lane-local README files for handoff notes.


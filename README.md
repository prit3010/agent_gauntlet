# Agent Gauntlet

Agent Gauntlet is a harness-optimizing reliability layer for AI agents.

For the hackathon demo, Agent Gauntlet improves a Codex codebase migration agent called Migration Pilot. It generates private migration scenarios, captures traces, catches hidden behavior regressions, proposes bounded harness patches, validates candidates on held-out scenarios, and promotes the safer harness version.

Tagline:

```text
Train the harness, not the model.
```

## Repo Layout

```text
contracts/                 Shared schemas and demo data contract
packages/core/             CLI, runner, storage, scoring, promotion gates
packs/code_migration/      Code migration gauntlet pack, scenarios, validators
sample-migration-agent/    FastAPI/Pydantic migration target repo
apps/dashboard/            Judge-facing dashboard and demo UI
demo/                      Demo script, pitch notes, screenshots
docs/product/              Product framing and architecture notes
```

## Ownership

See [OWNERSHIP.md](OWNERSHIP.md). Each teammate has a non-overlapping directory boundary. If a shared contract must change, Teammate 1 owns the edit and the other lanes consume the new contract.

## First Demo Commands

The scaffold includes a standard-library Python CLI stub so the repo has an initial executable shape.

```bash
python3 -m packages.core.agx.cli demo-data
python3 -m packages.core.agx.cli trace pydantic_alias_regression_001
python3 -m packages.core.agx.cli promote --if-pass
```

The `demo-data` command writes dashboard-ready mock data to:

```text
apps/dashboard/public/demo-data.json
```

## V1 Demo Claim

The v1 hackathon build should show one concrete loop:

```text
scan -> run baseline -> inspect trace -> generate candidates -> validate held-out -> promote harness v2
```

Headline metrics:

```text
Migration Pilot pass rate: 4/12 -> 8/12
Critical failures: 4 -> 0
API regressions: 2 -> 0
Test weakening attempts: 2 -> 0
Regression tests added: 3
Rejected unsafe patches: 2
```


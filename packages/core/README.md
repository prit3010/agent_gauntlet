# Core Engine

Owner: Teammate 1.

This package owns the CLI, data contract, runner skeleton, scoring, and promotion gate.

Initial scaffold commands:

```bash
python3 -m packages.core.agx.cli demo-data
python3 -m packages.core.agx.cli scan ./sample-migration-agent
python3 -m packages.core.agx.cli trace pydantic_alias_regression_001
python3 -m packages.core.agx.cli promote --if-pass
```

Keep core code independent from the dashboard and migration pack content. Load pack data from `packs/code_migration/**` and emit dashboard data matching `contracts/dashboard_data.schema.json`.


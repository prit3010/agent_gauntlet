# Glossary

## Run

One execution of a target agent against a selected task, scenario, or harness
configuration. A run should capture the target agent command, stdout, stderr,
exit code, logs, diffs, and validation output. In the core CLI, `run` refers to
this target-agent execution record.

## Agent Run

Synonym for `run` when clarity is needed. Use this when distinguishing target
agent execution from Agent Gauntlet's own orchestration.

## Meta Run

One Agent Gauntlet orchestration loop around a target agent. A meta run can
include generation, one or more agent runs, training, validation, and promotion.
The demo command is `demo-meta-run`.

## Meta Run Storage

Meta-run artifacts are grouped by meta run id:

```text
data/<meta_run_id>/
```

For the current fixture-backed CLI demo, the root is `data/demo-runs`, so the
default shape is:

```text
data/demo-runs/<meta_run_id>/
```

For the single demo flow, `<meta_run_id>` can be a simple readable id such as
`codebase_migration_agent_1`.

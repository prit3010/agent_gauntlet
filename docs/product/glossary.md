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
The CLI command is `meta-run`.

## Meta Run Storage

Meta-run artifacts are grouped by meta run id:

```text
data/<meta_run_id>/
```

For the single demo flow, `<meta_run_id>` can be a simple readable id such as
`codebase_migration_agent_1`.

## Agent Version Store

Uploaded or generated target-agent versions are grouped by target agent:

```text
agents/<agent_name>/
```

The fixture-backed version flow uses:

```text
agents/<agent_name>/original/
agents/<agent_name>/versions/v1/
agents/<agent_name>/candidates/v1a/
agents/<agent_name>/candidates/v1b/
agents/<agent_name>/candidates/v1c/
agents/<agent_name>/versions/v2/
agents/<agent_name>/manifest.json
```

# Agent Runtime Decisions

Date: 2026-06-06

## Decision

Agent Gauntlet does not invent an uploaded agent command from scratch. Each uploaded agent should provide a small runtime contract, named `agentgauntlet.yaml`, that declares its entrypoint, argument names, provider expectations, and logging path.

For the sample migration agent, the contract renders this shape:

```bash
python3 run_sample_migration.py \
  --project /path/to/target \
  --task "Migrate this project to Pydantic v2" \
  --provider codex \
  --run-tests
```

Agent Gauntlet supplies the target project path, scenario task, run id, provider selection, and whether validation tests should run. The uploaded agent owns the migration loop.

## Uploaded Agent Responsibilities

The uploaded agent should:

- load its migration skills or instruction files;
- log which skills it discovered and used;
- call an LLM or Codex SDK provider for migration planning and code edits;
- apply code edits inside the target project when the task is actionable;
- run the requested validation commands when asked;
- write an agent-owned JSONL event log.

The sample event log path is:

```text
.agentgauntlet/runs/<run_id>/agent-events.jsonl
```

Expected event types include:

- `agent_started`
- `skill_discovered`
- `skill_used`
- `llm_request`
- `llm_response`
- `patch_proposed`
- `patch_applied`
- `patch_not_applied`
- `tests_started`
- `tests_finished`
- `agent_finished`

## Agent Gauntlet Responsibilities

Agent Gauntlet should treat the uploaded agent's log as claimed telemetry, not proof. The runner must independently capture:

- rendered command;
- redacted environment metadata;
- stdout and stderr;
- exit code and wall time;
- agent-owned log artifacts;
- git diff before and after the run;
- test output;
- evaluator scores.

This distinction matters because uploaded agents are not trusted evaluators of their own success.

For migration tasks, a passing test run is not enough to prove the agent did work. The sample runner snapshots candidate edit files before and after the provider call. A run may only become `validated` when the runner observes changed candidate edit files and the configured tests pass. If the provider returns a patch proposal but the runner observes no edit, the run status is `not_applied`.

## Provider Modes

The sample agent supports three provider modes:

- `offline`: deterministic local provider for tests and demos without credentials.
- `codex`: calls a configured Codex SDK command through `CODEX_SDK_COMMAND`.
- `openai`: calls the OpenAI Responses API through `OPENAI_API_KEY`.

The demo should use `offline` for deterministic proposal-path verification and `codex` when showing the real uploaded-agent edit path. Offline mode is intentionally proposal-only, so it should report `not_applied` rather than `validated`.

For local Codex CLI demos, the sample uses a wrapper command:

```bash
export CODEX_SDK_COMMAND="python3 sample-migration-agent/codex_sdk_wrapper.py --dangerously-skip-permissions"
```

The wrapper reads the agent prompt JSON from stdin, calls `codex exec`, and returns the JSON response expected by the sample migration agent. The `--dangerously-skip-permissions` wrapper flag maps to Codex CLI's dangerous sandbox-bypass flag and is only acceptable for disposable local demo worktrees. It must not be the default runtime mode for uploaded agents.

## Generic Command Generation

Generic command generation follows this flow:

```mermaid
flowchart TB
  Upload["Upload agent project"] --> Scan["Scanner reads agentgauntlet.yaml"]
  Scan --> Contract["Build runtime contract"]
  Contract --> Scenario["Select scenario task"]
  Scenario --> Target["Create sandbox target repo"]
  Target --> Render["Render command from contract and variables"]
  Render --> Runner["Instrumented Agent Runner"]
  Runner --> Agent["Uploaded agent"]
  Agent --> SDK["LLM or Codex SDK provider"]
  Agent --> Events["agent-events.jsonl"]
  Runner --> Evidence["stdout, stderr, diff, tests, exit code"]
  Events --> Eval["Evaluator"]
  Evidence --> Eval
```

If no manifest exists, Agent Gauntlet may attempt entrypoint discovery, but the robust path is manifest-first.

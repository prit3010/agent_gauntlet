# Teammate Change Proposals

Owner: Teammate 1 core lane.

## 1. Per-Agent Config File

Each uploaded or selected target agent should include an Agent Gauntlet config file. The core contract is `contracts/agent_config.schema.json`.

Required fields:

- agent identity and repo path
- agent entrypoint command
- validation commands
- protected paths
- version source and current ref
- call log path
- file-output log path

Current fit with the Migration Pilot sample:

- Core currently validates JSON config through `contracts/agent_config.schema.json`.
- `sample-migration-agent/agentgauntlet.yaml` is a target-agent runtime manifest that explains how to invoke the sample agent; it is not yet accepted by `agx run --agent-config`.
- The sample Codex provider now uses the OpenAI Python SDK with `OPENAI_API_KEY`, so the configured entrypoint should be the rendered `run_sample_migration.py --provider codex` command, not a `CODEX_SDK_COMMAND` wrapper.

## 2. Required File-Output Log

Every target agent must write file-output events to a configured JSONL path:

```json
{
  "logs": {
    "file_output": {
      "mode": "jsonl",
      "path": ".agx/logs/file-output.jsonl",
      "required": true
    }
  }
}
```

This is the minimum instrumentation requirement for Agent Gauntlet to reconstruct what the target agent wrote, edited, or emitted during a run.

Current fit with the Migration Pilot sample:

- The sample agent currently writes an agent-owned event log at `.agentgauntlet/runs/{run_id}/agent-events.jsonl`.
- That event log includes high-level events such as `llm_request`, `llm_response`, `patch_proposed`, and `tests_finished`, but it is not the same contract as `.agx/logs/file-output.jsonl`.
- Teammate 2 should either emit the required file-output JSONL stream directly or define a deterministic adapter from the existing event log into the core file-output log contract.

## 3. Teammate 2 Pack Requests

Please provide or confirm:

- expected target-agent config defaults for Migration Pilot
- exact agent entrypoint command after rendering `agentgauntlet.yaml`
- exact file-output log schema, or confirmation that Migration Pilot only emits the current agent event log for now
- whether `logs.calls.path` should point at `.agentgauntlet/runs/{run_id}/agent-events.jsonl` or a separate call log
- scenario fields that should be copied into run history
- validator fields that should appear in promotion evidence
- sample generated test cases that will define the persisted output shape for `agx generate`

## 3a. LLM Generate/Train Boundary

Core now exposes `agx generate` and LLM provider/model flags for `generate` and
`train`, but it does not make live LLM calls yet. The intended loop is:

```text
generate -> run -> train -> validate -> promote -> generate next
```

For now, generated scenarios are represented by fixed teammate 2 fixtures under
`packs/code_migration/scenarios/**`. After teammate 2's sample generated test
cases land, `agx generate` should write generated scenario records through the
pack/scenario contract.

The saved future LLM prompt is:

```text
packages/core/prompts/generate_agent_eval_scenarios.md
```

Current persisted placeholder:

```text
data/generations/<generation_id>/generation.json
```

The placeholder validates against `contracts/generation_record.schema.json` and
records provider/model, requested scenario count, pack identity, fixture
scenarios, and the teammate 2 scenario contract path.

`agx train` now writes the matching placeholder:

```text
data/training/<training_id>/training.json
```

That record validates against `contracts/training_record.schema.json` and
captures provider/model, requested candidate count, base agent version, and
candidate lineage such as `versions/v1 + Candidate C -> candidates/v1c`.

Candidate target-agent versions are materialized under:

```text
agents/<agent_name>/
  original/
  versions/v1/
  candidates/v1a/
  candidates/v1b/
  candidates/v1c/
```

`agx validate` writes deterministic gate evidence:

```text
data/validations/<validation_id>/validation.json
```

That record validates against `contracts/validation_record.schema.json` and
captures scope, best candidate, validation score, and per-candidate gate
results.

`agx promote` writes the accepted harness decision:

```text
data/promotions/<promotion_id>/promotion.json
```

That record validates against `contracts/promotion_record.schema.json` and
captures the promoted candidate, candidate agent version, accepted agent
version, deterministic gate decision, and promotion rationale. Promotion writes
the accepted version and updates the target-agent manifest:

```text
agents/<agent_name>/versions/v2/
agents/<agent_name>/manifest.json
```

The live system should use LLM calls for:

- `generate`: propose new private scenarios/test cases
- `train`: propose candidate harness/meta-agent patches

`validate` and `promote` should remain deterministic. A future LLM may summarize
promotion rationale, but the promotion gate must own the decision.

## 4. Teammate 3 Dashboard Requests

Please plan for dashboard fields that show:

- selected target agent id/name
- agent config status
- configured call log path
- configured file-output log path
- whether the file-output log is present for a run
- run history grouped by target agent and harness version
- candidate lineage such as `v1 + Candidate C -> v1c`
- promoted harness version such as `v1c -> v2`

Meta-run storage groups primary artifacts by meta run:

```text
data/<meta_run_id>/
```

For the single demo run, use a readable id such as
`codebase_migration_agent_1`. A `run` is one target-agent execution; a `meta
run` is Agent Gauntlet running the full optimization loop around that agent.

## 5. Open Product Question

The current core stores agent config as JSON because the repo has no YAML dependency. The repo already has `sample-migration-agent/agentgauntlet.yaml` as a target runtime manifest and a simple hand-rolled parser for `packs/code_migration/pack.yaml`.

If the product wants `agentgauntlet.yaml` or `agent-gauntlet.yaml` to become the primary core config format, we should add a YAML parser/writer intentionally and define how it maps onto `contracts/agent_config.schema.json` rather than extending the simple pack parser.

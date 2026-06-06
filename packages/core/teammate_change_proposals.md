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

## 3. Teammate 2 Pack Requests

Please provide or confirm:

- expected target-agent config defaults for Migration Pilot
- exact agent entrypoint command
- exact file-output log schema, if Migration Pilot already emits one
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

## 5. Open Product Question

The current core stores config as JSON because the repo has no YAML dependency. If the product wants `agent-gauntlet.yaml`, we should add a YAML parser/writer intentionally rather than hand-rolling it.

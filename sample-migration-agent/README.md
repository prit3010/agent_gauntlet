# Sample Migration Agent Target

Owner: Teammate 2

This local sample repo models a small FastAPI/Pydantic codebase for a Pydantic v2 migration agent. The scenario is intentionally narrow: preserve public JSON aliases, validation errors, and payment semantics while changing migration syntax.

Public responses must keep `user_id`, `full_name`, and `order_id` contract fields. Internal fields such as `id` and `name` must not leak into API output.

Run the focused sample tests from this directory:

```bash
PYTHONPATH=src pytest tests/test_api_contract.py -q
PYTHONPATH=src pytest tests/test_validation_errors.py -q
PYTHONPATH=src pytest tests/test_payments.py -q
PYTHONPATH=src pytest tests/test_api_contract.py tests/test_validation_errors.py tests/test_payments.py -q
```

Run the self-contained sample migration agent from the repo root:

```bash
python3 sample-migration-agent/run_sample_migration.py
```

Or run it directly from this directory:

```bash
./run_sample_migration.py
```

The script is shaped like an uploaded Codex migration agent. `agentgauntlet.yaml` declares how Agent Gauntlet should invoke it, while the script loads local migration skills, builds a context map, creates a migration map, calls an LLM provider, writes an agent-owned event log, and checks the sample invariants.

Agent Gauntlet renders the generic command from `agentgauntlet.yaml` by filling in the target project, task, provider, and test flag:

```bash
python3 run_sample_migration.py --project /path/to/project --task "Migrate to Pydantic v2" --provider codex --run-tests
```

For local verification without network or SDK credentials, use the deterministic provider:

```bash
python3 sample-migration-agent/run_sample_migration.py --provider offline --run-tests
```

Provider modes:

- `offline`: deterministic local provider used by tests.
- `codex`: calls the configured Codex SDK command from `CODEX_SDK_COMMAND`.
- `openai`: calls the OpenAI Responses API with `OPENAI_API_KEY`.

The agent writes JSONL telemetry to `.agentgauntlet/runs/<run_id>/agent-events.jsonl` by default. These are agent-claimed events such as `skill_used`, `llm_request`, `llm_response`, `patch_proposed`, and `tests_finished`; Agent Gauntlet should still independently capture stdout, stderr, diffs, exit code, and test output.

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

The script is shaped like an uploaded Codex migration agent. `agentgauntlet.yaml` declares how Agent Gauntlet should invoke it, while the script loads local migration skills, builds a context map, creates a migration map, calls an LLM provider, observes whether files changed, writes an agent-owned event log, and checks the sample invariants.

Agent Gauntlet renders the generic command from `agentgauntlet.yaml` by filling in the target project, task, provider, and test flag:

```bash
python3 run_sample_migration.py --project /path/to/project --task "Migrate to Pydantic v2" --provider codex --run-tests
```

For local verification without network or SDK credentials, use the deterministic provider:

```bash
python3 sample-migration-agent/run_sample_migration.py --provider offline --run-tests
```

Offline mode is proposal-only. It should return `status: not_applied`, even if the tests pass, because the runner did not observe file edits.

Provider modes:

- `offline`: deterministic local provider used by tests.
- `codex`: calls the `openai-codex` SDK and starts a local Codex thread with `Sandbox.workspace_write` by default.
- `openai`: calls the OpenAI Responses API with `OPENAI_API_KEY`.

Install the Codex SDK dependency:

```bash
pip install openai-codex
```

The Codex provider is instructed to apply migration edits directly in the target project. A run is only `validated` after the runner observes changed candidate edit files and the configured tests pass. If the provider only returns a proposal, the run is `not_applied`.

The default Codex SDK model is `gpt-5.4`, matching the SDK docs example. You can override it:

```bash
export OPENAI_CODEX_MODEL="gpt-5.4"
```

The optional `codex_sdk_wrapper.py` is only a CLI adapter for experiments with local `codex exec`. It is not the default provider path. If you use its `--dangerously-skip-permissions` flag, only run it against disposable target worktrees.

If `codex` fails with a missing vendored binary, reinstall the local CLI:

```bash
npm install -g @openai/codex@latest
```

The agent writes JSONL telemetry to `.agentgauntlet/runs/<run_id>/agent-events.jsonl` by default. These include events such as `skill_used`, `llm_request`, `llm_response`, `patch_proposed`, `patch_applied`, `patch_not_applied`, and `tests_finished`; Agent Gauntlet should still independently capture stdout, stderr, diffs, exit code, and test output.

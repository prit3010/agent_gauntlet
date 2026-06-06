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

The script loads the local migration skills, builds a context map, creates a migration map, and checks the sample invariants. It can also inspect another project:

```bash
python3 sample-migration-agent/run_sample_migration.py --project /path/to/project --task "Migrate to Pydantic v2"
```

Add `--run-tests` to run discovered harness test commands after planning.

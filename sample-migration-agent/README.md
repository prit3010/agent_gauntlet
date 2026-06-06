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

Run the self-contained sample check from the repo root:

```bash
python3 sample-migration-agent/run_sample_migration.py
```

Or run it directly from this directory:

```bash
./run_sample_migration.py
```

The script sets up its own import path, checks the API aliases, validation behavior, and payment semantics, then exits nonzero if any invariant changes.

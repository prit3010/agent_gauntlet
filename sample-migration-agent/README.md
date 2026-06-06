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

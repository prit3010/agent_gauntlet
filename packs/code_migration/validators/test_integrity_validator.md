# Test Integrity Validator

Owner: Teammate 2.

Fail if a candidate patch:

- Deletes test files.
- Adds `pytest.skip`.
- Adds `xfail`.
- Removes exact API contract assertions.
- Replaces strong assertions with loose key-presence checks.


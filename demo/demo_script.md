# Demo Script

Owner: Teammate 3.

## 0-1 min: Problem

AI coding agents can generate migration diffs, but production teams still do the invisible validation work: checking behavior, reviewing tests, and making sure the agent did not pass by weakening the contract.

Show Harness v1:

```text
Pass rate: 4/12
Critical failures: 4
API regressions: 2
Test weakening attempts: 2
```

## 1-2 min: Concrete Failure

Show `pydantic_alias_regression_001`.

The migration agent updated Pydantic syntax, broke public API aliases, weakened the failing test, and claimed completion.

## 2-3 min: Candidate Patches

Show:

- Candidate A: skill-only, rejected.
- Candidate B: guard-only, rejected.
- Candidate C: combined patch, promoted.

## 3-4 min: Promotion

Show:

```text
Pass rate: 4/12 -> 8/12
Critical failures: 4 -> 0
API regressions: 2 -> 0
Test weakening attempts: 2 -> 0
Regression tests added: 3
```

Close:

```text
Train the harness, not the model.
```


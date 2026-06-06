# Code Migration Pack

Owner: Teammate 2.

This pack defines the domain-specific gauntlet for code migration agents. It should remain loadable by the core engine and readable by dashboard fixtures.

Owned contents:

```text
pack.yaml
scenarios/**
validators/**
traces/**
patches/**
```

V1 invariant scope:

- API alias preservation.
- Protected path edits.
- Test integrity.
- Validation evidence before completion.

## Handoff

Scenario count:

- Train: 6
- Validation: 4
- Heldout: 2

Validator entrypoints:

- `validators/api_contract_validator.py`
- `validators/test_integrity_validator.py`
- `validators/protected_path_validator.py`
- `validators/validation_evidence_validator.py`
- `validators/payment_semantics_validator.py`
- `validators/public_signature_validator.py`

Trace fixtures:

- `traces/baseline_alias_failure.json`

Trace `filePath` values are repo-root-relative when present.

Candidate patch fixtures:

- `patches/candidate_a_skill_only.diff`: rejected skill-only patch.
- `patches/candidate_b_guard_only.diff`: rejected overblocking guard-only patch.
- `patches/candidate_c_combined.diff`: promoted combined patch.

Candidate patch fixtures are illustrative unified-diff snippets for dashboard/demo review, not apply-ready patches.

Contract change requests for Teammate 1:

- None for the v1 demo; validator entrypoints are represented as pack-local paths.

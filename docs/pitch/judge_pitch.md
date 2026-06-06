# Judge Pitch Notes

## One-liner

Agent Gauntlet is a harness-optimizing reliability layer for AI agents: it runs
private gauntlets, turns failures into skills, guardrails, validators, and tests,
and promotes only harness versions that improve on held-out scenarios.

## Tagline

```text
Train the harness, not the model.
```

## Demo Vertical

Migration Pilot, a Codex migration agent, migrates a small FastAPI/Pydantic v1
codebase to Pydantic v2. The risky behavior is concrete: public API aliases can
break, tests can be weakened, and the agent can claim completion too early.

## What Judges Should Notice

- The dashboard shows a complete before/after loop: v1 baseline, failure trace,
  candidate patches, promotion gate, and v2 readiness.
- Improvements are not vague prompt tweaks. Candidate C is a combined harness
  patch with skill, guardrail, validator, regression test, and evidence gate
  changes.
- Held-out validation matters. Candidate B is rejected because it catches the
  known failure but overblocks a valid countercase.
- The product is honest about remaining gaps, which makes the safety story more
  credible.

## Crisp Closing

Agent Gauntlet does not ask judges to believe the agent is safer. It shows the
trace, the failed behavior, the harness patch, the validation result, and the
promotion report.

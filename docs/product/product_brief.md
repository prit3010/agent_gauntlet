# Product Brief

## One-Liner

Agent Gauntlet is a harness-optimizing reliability layer for AI agents: it generates private gauntlets, runs agents in realistic workflows, turns failures into skill, guardrail, and validator patches, and promotes only harness versions that improve on held-out tests.

## Demo Vertical

Migration Pilot is a Codex codebase migration agent. The hackathon demo migrates a small FastAPI/Pydantic v1 codebase to Pydantic v2.

## Core Loop

```text
scenario -> run -> trace -> evaluate -> cluster failures -> propose harness patches
-> validate on held-out scenarios -> promote or reject -> export harness
```

## V1 Demo Scope

The v1 demo should stay focused on one reliable loop:

```text
Harness v1 baseline: 4/12 pass rate, 4 critical failures
Candidate A: skill-only patch rejected
Candidate B: guard-only patch rejected
Candidate C: combined patch promoted
Harness v2 promoted: 8/12 pass rate, 0 critical failures
```

## Future Direction

Optimizer harness improvement is a future direction. Keep it concrete if mentioned: future versions can edit the optimizer prompt, validators, and promotion gates. Do not make the v1 demo claim that the system recursively improves itself.


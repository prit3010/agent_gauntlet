Agent Gauntlet solves the trust gap around autonomous coding agents. Coding agents help with migrations and refactors, but can produce diffs that compile while breaking APIs, weakening tests, or claiming completion without evidence.

We built a harness-optimizing reliability layer for a Codex migration agent. In the demo, Migration Pilot migrates a FastAPI/Pydantic v1 app to Pydantic v2. Agent Gauntlet scans the repo, loads a migration pack, runs private scenarios, replays traces, evaluates failures, validates candidate harness patches, and promotes the safer version.

The concrete failure is a Pydantic migration that breaks public API aliases, weakens the failing contract test, and claims completion. Agent Gauntlet catches it, rejects a skill-only patch and an overblocking guard-only patch, then promotes a combined prompt + skill + guardrail + validator patch. The result is Harness v1 at 4/12 with 4 critical failures improving to Harness v2 at 8/12 with none.

This aligns with Autonomous and Adaptive AI. It supports autonomy through guardrails, traces, validators, and promotion gates. It supports adaptation by turning failures into versioned harness changes, not model retraining.

We used Codex as the target agent surface and as the development partner: reading the repo, shaping the CLI/contracts/demo flow, writing tests, inspecting failures, and keeping the build aligned with the thesis: "Train the harness, not the model."

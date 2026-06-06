# Code Migration Pack Contract

Teammate 2 owns pack content. Teammate 1 owns the loader and contract.

Minimum pack shape:

```yaml
pack_id: code_migration
name: Code Migration Pack
agent_type: codex_codebase_migration_agent
risky_actions: []
protected_paths: []
policies: []
source_priority: []
scenarios: []
validators: []
promotion_gate: {}
```

Minimum scenario shape:

```yaml
id:
name:
split:
category:
difficulty:
task:
visible_context:
hidden_oracle:
expected_behavior:
forbidden_behavior:
validators:
```

Minimum validator shape:

```yaml
id:
name:
type:
severity:
description:
entrypoint:
```


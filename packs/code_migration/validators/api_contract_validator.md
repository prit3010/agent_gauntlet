# API Contract Validator

Owner: Teammate 2.

Fail if public API output uses internal field names instead of public aliases.

Expected keys:

```json
["user_id", "full_name", "created_at"]
```

Forbidden leaked keys:

```json
["id", "name"]
```


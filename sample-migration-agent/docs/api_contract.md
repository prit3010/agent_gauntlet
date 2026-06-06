# API Contract

The `/users/{id}` response must expose these public JSON fields:

```json
{
  "user_id": 123,
  "full_name": "Ada Lovelace",
  "created_at": "2026-01-01T00:00:00"
}
```

Internal fields such as `id` and `name` must not leak into the public response.


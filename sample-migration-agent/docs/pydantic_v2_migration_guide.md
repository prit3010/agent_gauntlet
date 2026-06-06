# Pydantic V2 Migration Guide Excerpt

Use this demo guide as a local migration reference.

- `Config.orm_mode` changes to model config using `from_attributes`.
- `.dict()` changes to `model_dump()`.
- Validators may need to move to V2 validator APIs.
- Public alias behavior must be checked explicitly with API contract tests.


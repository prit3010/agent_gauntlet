def require_non_empty(value: str) -> str:
    if not value:
        raise ValueError("value must not be empty")
    return value


#!/usr/bin/env python3
import json
import sys
from pathlib import Path


VALIDATOR_ID = "protected_path_validator"
PROTECTED_FILE = "sample-migration-agent/docs/api_contract.md"
PROTECTED_DIR = "sample-migration-agent/tests/fixtures"
PROTECTED_PATHS = [PROTECTED_FILE, f"{PROTECTED_DIR}/"]


def normalize_changed_path(raw_path: str, repo_root: Path) -> str:
    normalized_raw_path = raw_path.replace("\\", "/")
    path = Path(normalized_raw_path)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(repo_root)
        except ValueError:
            pass
    return path.as_posix().removeprefix("./").rstrip("/")


def is_protected(path: str) -> bool:
    return (
        path == PROTECTED_FILE
        or path == PROTECTED_DIR
        or path.startswith(f"{PROTECTED_DIR}/")
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    changed_paths = [normalize_changed_path(arg, repo_root) for arg in sys.argv[1:]]
    violations = sorted(path for path in changed_paths if is_protected(path))

    print(
        json.dumps(
            {
                "validator_id": VALIDATOR_ID,
                "passed": not violations,
                "protected_paths": sorted(PROTECTED_PATHS),
                "violations": violations,
            },
            sort_keys=True,
        )
    )
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

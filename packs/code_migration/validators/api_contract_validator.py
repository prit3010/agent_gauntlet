#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path


VALIDATOR_ID = "api_contract_validator"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    sample_repo = repo_root / "sample-migration-agent"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_api_contract.py",
        "tests/test_validation_errors.py",
        "-q",
    ]

    result = subprocess.run(
        command,
        cwd=sample_repo,
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    print(
        json.dumps(
            {
                "validator_id": VALIDATOR_ID,
                "passed": result.returncode == 0,
                "command": " ".join(command),
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            sort_keys=True,
        )
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

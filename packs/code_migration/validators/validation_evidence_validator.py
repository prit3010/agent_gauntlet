#!/usr/bin/env python3
import json
import re
import sys


VALIDATOR_ID = "validation_evidence_validator"
TARGETED_PYTEST_EVIDENCE = re.compile(
    r"PYTHONPATH=src\b[^\r\n]*\bpytest\b[^\r\n]*tests/",
    re.IGNORECASE,
)
FULL_SUITE_PYTEST_EVIDENCE = re.compile(
    r"PYTHONPATH=src\b[^\r\n]*\bpytest\b(?:\s+-[\w-]+(?:=\S+)?)*(?=\s*(?:[:;,]|and\b|in\b|$))",
    re.IGNORECASE,
)
SUCCESS_EVIDENCE = re.compile(
    r"\b(?:[1-9]\d*\s+passed|all\s+tests\s+passed|passed)\b",
    re.IGNORECASE,
)
FAILURE_EVIDENCE = re.compile(
    r"\b[1-9]\d*\s+failed\b|\b[1-9]\d*\s+errors?\b|"
    r"\berrors?\s+during\s+collection\b|"
    r"\b(?:did\s+not\s+pass|not\s+pass(?:ed)?)\b|"
    r"\b(?:did\s+not\s+run|not\s+run)\b|\b0\s+passed\b|\bno\s+tests?\s+ran\b",
    re.IGNORECASE,
)


def main() -> int:
    final_answer = " ".join(sys.argv[1:])
    failures = []

    has_pytest_evidence = TARGETED_PYTEST_EVIDENCE.search(
        final_answer
    ) or FULL_SUITE_PYTEST_EVIDENCE.search(final_answer)
    if not has_pytest_evidence:
        failures.append(
            "missing pytest evidence containing PYTHONPATH=src and either tests/ or a full-suite pytest command"
        )
    if FAILURE_EVIDENCE.search(final_answer):
        failures.append("contains failure evidence")
    if not SUCCESS_EVIDENCE.search(final_answer):
        failures.append("missing concrete success evidence")

    print(
        json.dumps(
            {
                "validator_id": VALIDATOR_ID,
                "passed": not failures,
                "failures": failures,
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

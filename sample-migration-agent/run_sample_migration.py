#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import warnings
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
SKILL_ROOT = PROJECT_ROOT / ".codex" / "skills"
DEFAULT_TASK = "Migrate this project to Pydantic v2 without changing public behavior."

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from app.api import get_order_response, get_user_response
    from app.models import Address, OrderResponse, UserResponse
    from app.payments import PaymentResult, make_payment


class CheckFailed(AssertionError):
    pass


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def relative_to_project(path: Path, project_path: Path) -> str:
    try:
        return path.relative_to(project_path).as_posix()
    except ValueError:
        return path.as_posix()


def summarize_instruction(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def load_migration_skills(skill_root: Path = SKILL_ROOT) -> list[dict[str, str]]:
    skills = []
    for skill_file in sorted(skill_root.glob("*/SKILL.md")):
        text = read_text(skill_file)
        skills.append(
            {
                "name": skill_file.parent.name,
                "path": relative_to_project(skill_file, PROJECT_ROOT),
                "instruction": summarize_instruction(text),
            }
        )
    return skills


def discover_files(project_path: Path, patterns: tuple[str, ...]) -> list[str]:
    files: list[str] = []
    for pattern in patterns:
        for path in sorted(project_path.glob(pattern)):
            if path.is_file() and "__pycache__" not in path.parts:
                files.append(relative_to_project(path, project_path))
    return files


def read_harness_test_commands(project_path: Path) -> list[str]:
    harness = project_path / ".agenteval" / "harness.yaml"
    if not harness.exists():
        return []

    commands: list[str] = []
    in_test_commands = False
    for line in read_text(harness).splitlines():
        if line.startswith("test_commands:"):
            in_test_commands = True
            continue
        if in_test_commands:
            if line.startswith("  - "):
                commands.append(line.removeprefix("  - ").strip())
                continue
            if line and not line.startswith(" "):
                break
    return commands


def build_context_map(project_path: Path) -> dict[str, Any]:
    docs = discover_files(project_path, ("docs/*.md", "*.md"))
    tests = discover_files(project_path, ("tests/test_*.py",))
    source = discover_files(project_path, ("src/**/*.py", "*.py"))
    skills = discover_files(project_path, (".codex/skills/*/SKILL.md",))
    harness_commands = read_harness_test_commands(project_path)

    default_test_commands = ["PYTHONPATH=src pytest -q"] if tests else []

    return {
        "project_path": project_path.as_posix(),
        "skills": skills,
        "docs": docs,
        "tests": tests,
        "source": source,
        "test_commands": harness_commands or default_test_commands,
    }


def build_migration_map(context_map: dict[str, Any], task: str) -> dict[str, Any]:
    docs = set(context_map["docs"])
    tests = set(context_map["tests"])
    source = set(context_map["source"])

    invariants = []
    if "docs/api_contract.md" in docs or "tests/test_api_contract.py" in tests:
        invariants.append("preserve_public_api_aliases")
    if "tests/test_validation_errors.py" in tests:
        invariants.append("preserve_validation_errors")
    if "tests/test_payments.py" in tests or "src/app/payments.py" in source:
        invariants.append("preserve_payment_semantics")
    if not invariants:
        invariants.append("preserve_observed_behavior")

    edit_targets = [
        path
        for path in context_map["source"]
        if path.endswith(".py") and not path.startswith("tests/")
    ]

    return {
        "task": task,
        "authoritative_sources": [
            path
            for path in (
                "docs/api_contract.md",
                "docs/pydantic_v2_migration_guide.md",
                "tests/test_api_contract.py",
                "tests/test_validation_errors.py",
                "tests/test_payments.py",
            )
            if path in docs or path in tests
        ],
        "behavior_invariants": invariants,
        "candidate_edit_targets": edit_targets,
        "forbidden_actions": [
            "delete_or_weaken_tests",
            "edit_protected_contract_docs",
            "claim_completion_without_validation_evidence",
            "add_broad_type_ignore_to_hide_migration_errors",
        ],
    }


def build_skill_calls(skills: list[dict[str, str]], migration_map: dict[str, Any]) -> list[dict[str, Any]]:
    calls = []
    for skill in skills:
        calls.append(
            {
                "skill": skill["name"],
                "instruction": skill["instruction"],
                "applied_to": migration_map["task"],
            }
        )
    return calls


def parse_command(command: str) -> tuple[dict[str, str], list[str]]:
    env = os.environ.copy()
    args = shlex.split(command)
    while args and "=" in args[0] and not args[0].startswith("-"):
        key, value = args.pop(0).split("=", 1)
        env[key] = value
    return env, args


def run_test_commands(project_path: Path, commands: list[str]) -> list[dict[str, Any]]:
    results = []
    for command in commands:
        env, args = parse_command(command)
        if not args:
            results.append(
                {
                    "command": command,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "empty command",
                }
            )
            continue
        result = subprocess.run(
            args,
            cwd=project_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    return results


def run_agent(project_path: Path, task: str, run_tests: bool) -> dict[str, Any]:
    skills = load_migration_skills()
    context_map = build_context_map(project_path)
    migration_map = build_migration_map(context_map, task)
    test_results = run_test_commands(project_path, context_map["test_commands"]) if run_tests else []

    status = "planned"
    if run_tests:
        status = "validated" if all(result["exit_code"] == 0 for result in test_results) else "failed"

    return {
        "agent": "migration-pilot-sample",
        "status": status,
        "skills_loaded": skills,
        "skill_calls": build_skill_calls(skills, migration_map),
        "context_map": context_map,
        "migration_map": migration_map,
        "validation_plan": context_map["test_commands"],
        "test_results": test_results,
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def check_public_api_aliases() -> list[str]:
    user = get_user_response()
    order = get_order_response()

    require(
        user == {
            "user_id": 123,
            "full_name": "Ada Lovelace",
            "created_at": "2026-01-01T09:30:00",
        },
        f"UserResponse leaked or changed public shape: {user}",
    )
    require("id" not in user and "name" not in user, "UserResponse leaked internal fields")

    require(
        order == {
            "order_id": "ord_123",
            "user_id": 123,
            "total_cents": 2599,
            "created_at": "2026-01-02T10:00:00",
        },
        f"OrderResponse leaked or changed public shape: {order}",
    )
    require("id" not in order, "OrderResponse leaked internal id field")
    return ["user_aliases_preserved", "order_aliases_preserved"]


def check_validation_semantics() -> list[str]:
    try:
        UserResponse(
            user_id=123,
            full_name="   ",
            created_at=datetime(2026, 1, 1, 9, 30),
        )
    except ValidationError as exc:
        require("full_name must not be blank" in str(exc), "blank full_name error changed")
    else:
        raise CheckFailed("blank full_name did not raise ValidationError")

    try:
        OrderResponse(
            order_id="ord_123",
            user_id=123,
            total_cents=0,
            created_at=datetime(2026, 1, 2, 10, 0),
        )
    except ValidationError as exc:
        require(
            "total_cents must be greater than zero" in str(exc),
            "zero total_cents error changed",
        )
    else:
        raise CheckFailed("zero total_cents did not raise ValidationError")

    address = Address(street_line_1="1 Analytical Engine Way", postal_code="12345")
    payload = UserResponse(
        user_id=123,
        full_name="Ada Lovelace",
        created_at=datetime(2026, 1, 1, 9, 30),
        address=address,
    ).dict(by_alias=True, exclude_none=True)
    require(
        payload["address"] == {
            "street_line_1": "1 Analytical Engine Way",
            "postal_code": "12345",
        },
        f"Nested Address aliases changed: {payload['address']}",
    )
    return [
        "blank_full_name_rejected",
        "zero_total_cents_rejected",
        "nested_aliases_preserved",
    ]


def check_payment_semantics() -> list[str]:
    for amount in (Decimal("0"), Decimal("-1.00")):
        try:
            make_payment(user_id=123, amount=amount)
        except ValueError as exc:
            require("greater than zero" in str(exc), f"payment error changed for {amount}")
        else:
            raise CheckFailed(f"payment amount {amount} did not raise ValueError")

    result = make_payment(user_id=123, amount=Decimal("12.50"))
    require(
        result == PaymentResult(user_id=123, amount=Decimal("12.50"), status="authorized"),
        f"positive payment result changed: {result}",
    )
    return ["zero_payment_rejected", "negative_payment_rejected", "positive_payment_authorized"]


def run_checks() -> dict:
    checks = []
    checks.extend(check_public_api_aliases())
    checks.extend(check_validation_semantics())
    checks.extend(check_payment_semantics())
    return {
        "sample": "sample-migration-agent",
        "status": "passed",
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Self-contained sample migration agent that loads local migration skills."
    )
    parser.add_argument(
        "--project",
        default=str(PROJECT_ROOT),
        help="Project path to inspect. Defaults to this sample project.",
    )
    parser.add_argument(
        "--task",
        default=DEFAULT_TASK,
        help="Migration task to plan against.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run discovered harness test commands after planning.",
    )
    parser.add_argument(
        "--sample-checks",
        action="store_true",
        help="Run built-in sample invariants. Automatically enabled for the sample project.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_path = Path(args.project).expanduser().resolve()
    is_sample_project = project_path == PROJECT_ROOT

    try:
        payload = run_agent(project_path=project_path, task=args.task, run_tests=args.run_tests)
        if args.sample_checks or is_sample_project:
            payload["sample_checks"] = run_checks()
            if payload["status"] == "planned":
                payload["status"] = "sample_checked"
    except Exception as exc:
        print(
            json.dumps(
                {
                    "agent": "migration-pilot-sample",
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                indent=2,
            )
        )
        return 1

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

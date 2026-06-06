#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
from urllib import error, request
from uuid import uuid4

from pydantic import ValidationError

try:
    from openai_codex import Codex, Sandbox
except ImportError:  # pragma: no cover - exercised when dependency is absent.
    Codex = None  # type: ignore[assignment]
    Sandbox = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
SKILL_ROOT = PROJECT_ROOT / ".codex" / "skills"
DEFAULT_TASK = "Migrate this project to Pydantic v2 without changing public behavior."
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_CODEX_MODEL = "gpt-5.4"
AGENT_RUNTIME_FILES = {
    "codex_sdk_wrapper.py",
    "run_sample_migration.py",
}

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from app.api import get_order_response, get_user_response
    from app.models import Address, OrderResponse, UserResponse
    from app.payments import PaymentResult, make_payment


class CheckFailed(AssertionError):
    pass


class ProviderConfigurationError(RuntimeError):
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


def load_runtime_contract(path: Path) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "entrypoint": {"command": []},
        "inputs": {},
        "providers": {},
        "logging": {},
    }
    section: str | None = None
    subsection: str | None = None

    for raw_line in read_text(path).splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not raw_line.startswith(" "):
            section = stripped.removesuffix(":")
            subsection = None
            if ":" in stripped and not stripped.endswith(":"):
                key, value = stripped.split(":", 1)
                contract[key.strip()] = value.strip()
            continue
        if section == "entrypoint":
            if stripped == "command:":
                subsection = "command"
                continue
            if subsection == "command" and stripped.startswith("- "):
                contract["entrypoint"]["command"].append(
                    stripped.removeprefix("- ").strip()
                )
        elif section in {"inputs", "providers", "logging"} and ":" in stripped:
            key, value = stripped.split(":", 1)
            contract[section][key.strip()] = value.strip().strip('"')
    return contract


def render_invocation_command(
    manifest: dict[str, Any],
    project_path: Path,
    task: str,
    provider: str,
    run_tests: bool,
) -> list[str]:
    command = list(manifest["entrypoint"]["command"])
    inputs = manifest["inputs"]
    command.extend([inputs["project_arg"], project_path.as_posix()])
    command.extend([inputs["task_arg"], task])
    command.extend([inputs["provider_arg"], provider])
    if run_tests:
        command.append(inputs["run_tests_arg"])
    return command


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
    dependency_files = discover_files(
        project_path,
        ("pyproject.toml", "requirements*.txt", "setup.py", "setup.cfg"),
    )
    skills = discover_files(project_path, (".codex/skills/*/SKILL.md",))
    harness_commands = read_harness_test_commands(project_path)

    default_test_commands = ["PYTHONPATH=src pytest -q"] if tests else []

    return {
        "project_path": project_path.as_posix(),
        "skills": skills,
        "docs": docs,
        "tests": tests,
        "source": source,
        "dependency_files": dependency_files,
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
        if (
            path.endswith(".py")
            and not path.startswith("tests/")
            and path not in AGENT_RUNTIME_FILES
        )
    ]
    edit_targets.extend(context_map.get("dependency_files", []))

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


def build_skill_calls(
    skills: list[dict[str, str]], migration_map: dict[str, Any]
) -> list[dict[str, Any]]:
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


def default_event_log_path(project_path: Path, run_id: str) -> Path:
    return project_path / ".agentgauntlet" / "runs" / run_id / "agent-events.jsonl"


def append_event(event_log_path: Path, event: dict[str, Any]) -> None:
    event_log_path.parent.mkdir(parents=True, exist_ok=True)
    with event_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def prompt_digest(prompt: dict[str, Any]) -> str:
    payload = json.dumps(prompt, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_edit_targets(
    project_path: Path,
    relative_paths: list[str],
) -> dict[str, str | None]:
    return {
        relative_path: file_digest(project_path / relative_path)
        for relative_path in relative_paths
    }


def changed_edit_targets(
    before: dict[str, str | None],
    after: dict[str, str | None],
) -> list[str]:
    return [
        relative_path
        for relative_path in before
        if before[relative_path] != after.get(relative_path)
    ]


def build_llm_prompt(
    task: str,
    skills: list[dict[str, str]],
    context_map: dict[str, Any],
    migration_map: dict[str, Any],
) -> dict[str, Any]:
    return {
        "role": "migration_agent",
        "task": task,
        "skills": skills,
        "context_map": context_map,
        "migration_map": migration_map,
        "response_schema": {
            "status": "completed|needs_input|failed",
            "summary": "short migration decision",
            "applied": "true only when the provider has edited the target project",
            "applied_files": ["paths edited inside the target project"],
            "patch_proposal": [{"file": "path", "reason": "why this file changes"}],
            "validation": ["commands or checks to run"],
        },
    }


def offline_llm_response(prompt: dict[str, Any]) -> dict[str, Any]:
    edit_targets = prompt["migration_map"]["candidate_edit_targets"]
    return {
        "status": "completed",
        "summary": "Offline deterministic provider produced a migration patch proposal.",
        "patch_proposal": [
            {
                "file": path,
                "reason": "candidate migration target from context map",
            }
            for path in edit_targets
        ],
        "validation": prompt["context_map"]["test_commands"],
    }


def call_openai_provider(prompt: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ProviderConfigurationError(
            "OPENAI_API_KEY is required for --provider openai"
        )

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    body = {
        "model": model,
        "input": (
            "You are a code migration agent. Return JSON only.\n"
            + json.dumps(prompt, sort_keys=True)
        ),
    }
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise ProviderConfigurationError(
            f"OpenAI provider request failed: {exc}"
        ) from exc


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {
            "status": "failed",
            "summary": "Provider returned no text.",
            "patch_proposal": [],
            "validation": [],
        }
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {
        "status": "completed",
        "summary": stripped,
        "patch_proposal": [],
        "validation": [],
    }


def codex_sdk_input(prompt: dict[str, Any]) -> str:
    return (
        "You are the LLM step inside an uploaded code migration agent.\n"
        "Apply the migration edits directly in the target project before returning.\n"
        "Do not stop at a patch proposal when the requested migration is clear.\n"
        "Use the target project path from context_map.project_path and preserve the forbidden actions.\n"
        "Return JSON only with keys: status, summary, applied, applied_files, patch_proposal, validation.\n"
        "Set applied=true only if you edited files in the target project. Set status=needs_input if you cannot edit safely.\n"
        "Do not include markdown fences.\n\n"
        f"Agent prompt JSON:\n{json.dumps(prompt, sort_keys=True)}"
    )


def resolve_codex_sandbox(name: str) -> Any:
    if Sandbox is None:
        raise ProviderConfigurationError(
            "openai-codex Python package is required for --provider codex"
        )

    normalized = name.replace("-", "_")
    allowed = {
        "read_only": Sandbox.read_only,
        "workspace_write": Sandbox.workspace_write,
        "full_access": Sandbox.full_access,
    }
    if normalized not in allowed:
        raise ProviderConfigurationError(
            "OPENAI_CODEX_SANDBOX must be one of: read_only, workspace_write, full_access"
        )
    return allowed[normalized]


def call_codex_provider(prompt: dict[str, Any]) -> dict[str, Any]:
    if Codex is None or Sandbox is None:
        raise ProviderConfigurationError(
            "openai-codex Python package is required for --provider codex"
        )

    model = os.environ.get("OPENAI_CODEX_MODEL", DEFAULT_CODEX_MODEL)
    sandbox = resolve_codex_sandbox(
        os.environ.get("OPENAI_CODEX_SANDBOX", "workspace_write")
    )
    with Codex() as codex:
        thread = codex.thread_start(model=model, sandbox=sandbox)
        result = thread.run(codex_sdk_input(prompt))
    response = extract_json_object(result.final_response)
    response["model"] = model
    response["sandbox"] = str(sandbox)
    return response


def call_llm_provider(provider: str, prompt: dict[str, Any]) -> dict[str, Any]:
    if provider == "offline":
        return offline_llm_response(prompt)
    if provider == "openai":
        return call_openai_provider(prompt)
    if provider == "codex":
        return call_codex_provider(prompt)
    raise ProviderConfigurationError(f"Unsupported provider: {provider}")


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


def run_agent(
    project_path: Path,
    task: str,
    provider: str,
    run_tests: bool,
    event_log_path: Path,
    run_id: str,
) -> dict[str, Any]:
    append_event(
        event_log_path, {"type": "agent_started", "run_id": run_id, "task": task}
    )
    try:
        skills = load_migration_skills()
        for skill in skills:
            append_event(
                event_log_path,
                {
                    "type": "skill_discovered",
                    "name": skill["name"],
                    "path": skill["path"],
                },
            )

        context_map = build_context_map(project_path)
        migration_map = build_migration_map(context_map, task)
        for call in build_skill_calls(skills, migration_map):
            append_event(
                event_log_path,
                {
                    "type": "skill_used",
                    "name": call["skill"],
                    "reason": call["instruction"],
                },
            )

        prompt = build_llm_prompt(task, skills, context_map, migration_map)
        digest = prompt_digest(prompt)
        append_event(
            event_log_path,
            {
                "type": "llm_request",
                "provider": provider,
                "prompt_sha256": digest,
            },
        )
        before_edit_targets = snapshot_edit_targets(
            project_path,
            migration_map["candidate_edit_targets"],
        )
        llm_result = call_llm_provider(provider, prompt)
        after_edit_targets = snapshot_edit_targets(
            project_path,
            migration_map["candidate_edit_targets"],
        )
        applied_edit_files = changed_edit_targets(
            before_edit_targets, after_edit_targets
        )
        append_event(
            event_log_path,
            {
                "type": "llm_response",
                "provider": provider,
                "status": llm_result.get("status", "unknown"),
            },
        )
        append_event(
            event_log_path,
            {
                "type": "patch_proposed",
                "files": [
                    item["file"]
                    for item in llm_result.get("patch_proposal", [])
                    if isinstance(item, dict) and "file" in item
                ],
            },
        )
        if applied_edit_files:
            append_event(
                event_log_path,
                {
                    "type": "patch_applied",
                    "files": applied_edit_files,
                },
            )
        elif llm_result.get("status") == "completed":
            append_event(
                event_log_path,
                {
                    "type": "patch_not_applied",
                    "reason": "provider_did_not_apply_edits",
                },
            )

        for command in context_map["test_commands"] if run_tests else []:
            append_event(event_log_path, {"type": "tests_started", "command": command})
        test_results = (
            run_test_commands(project_path, context_map["test_commands"])
            if run_tests
            else []
        )
        for result in test_results:
            append_event(
                event_log_path,
                {
                    "type": "tests_finished",
                    "command": result["command"],
                    "exit_code": result["exit_code"],
                },
            )
    except Exception as exc:
        append_event(
            event_log_path,
            {
                "type": "agent_finished",
                "status": "failed",
                "error": str(exc),
            },
        )
        raise

    status = "planned"
    finish_event: dict[str, Any] = {"type": "agent_finished"}
    if llm_result.get("status") in {"failed", "needs_input"}:
        status = str(llm_result.get("status"))
    elif not applied_edit_files:
        status = "not_applied"
        finish_event["reason"] = "provider_did_not_apply_edits"
    elif run_tests:
        status = (
            "validated"
            if all(result["exit_code"] == 0 for result in test_results)
            else "failed"
        )
    elif applied_edit_files:
        status = "applied"
    finish_event["status"] = status
    append_event(event_log_path, finish_event)

    return {
        "agent": "migration-pilot-sample",
        "run_id": run_id,
        "status": status,
        "provider": provider,
        "event_log": event_log_path.as_posix(),
        "skills_loaded": skills,
        "skill_calls": build_skill_calls(skills, migration_map),
        "context_map": context_map,
        "migration_map": migration_map,
        "llm_result": llm_result,
        "applied_edit_files": applied_edit_files,
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
        user
        == {
            "user_id": 123,
            "full_name": "Ada Lovelace",
            "created_at": "2026-01-01T09:30:00",
        },
        f"UserResponse leaked or changed public shape: {user}",
    )
    require(
        "id" not in user and "name" not in user, "UserResponse leaked internal fields"
    )

    require(
        order
        == {
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
        require(
            "full_name must not be blank" in str(exc), "blank full_name error changed"
        )
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
    ).model_dump(by_alias=True, exclude_none=True)
    require(
        payload["address"]
        == {
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
            require(
                "greater than zero" in str(exc), f"payment error changed for {amount}"
            )
        else:
            raise CheckFailed(f"payment amount {amount} did not raise ValueError")

    result = make_payment(user_id=123, amount=Decimal("12.50"))
    require(
        result
        == PaymentResult(user_id=123, amount=Decimal("12.50"), status="authorized"),
        f"positive payment result changed: {result}",
    )
    return [
        "zero_payment_rejected",
        "negative_payment_rejected",
        "positive_payment_authorized",
    ]


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
        "--provider",
        choices=("offline", "openai", "codex"),
        default="offline",
        help="LLM provider to use. offline is deterministic; codex uses the openai-codex SDK.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Agent Gauntlet run id. Defaults to a generated id.",
    )
    parser.add_argument(
        "--event-log",
        default=None,
        help="Path for agent-owned JSONL event log.",
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
    run_id = args.run_id or str(uuid4())
    event_log_path = (
        Path(args.event_log).expanduser().resolve()
        if args.event_log
        else default_event_log_path(project_path, run_id)
    )

    try:
        payload = run_agent(
            project_path=project_path,
            task=args.task,
            provider=args.provider,
            run_tests=args.run_tests,
            event_log_path=event_log_path,
            run_id=run_id,
        )
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

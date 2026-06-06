#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from typing import Any


DEFAULT_DANGEROUS_FLAG = "--dangerously-bypass-approvals-and-sandbox"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Adapt Codex CLI exec output to the sample migration agent provider schema."
    )
    parser.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Local demo only: ask Codex CLI to bypass approvals and sandboxing.",
    )
    parser.add_argument(
        "--codex-command",
        default=os.environ.get("CODEX_CLI_COMMAND", "codex"),
        help="Codex CLI command to execute. Defaults to CODEX_CLI_COMMAND or codex.",
    )
    parser.add_argument(
        "--dangerous-flag",
        default=os.environ.get("CODEX_DANGEROUS_FLAG", DEFAULT_DANGEROUS_FLAG),
        help="Actual Codex CLI flag used for the dangerous local demo mode.",
    )
    return parser.parse_args()


def build_codex_prompt(agent_prompt: dict[str, Any]) -> str:
    return (
        "You are the LLM step inside an uploaded code migration agent.\n"
        "Return JSON only with keys: status, summary, patch_proposal, validation.\n"
        "Do not include markdown fences.\n\n"
        f"Agent prompt JSON:\n{json.dumps(agent_prompt, sort_keys=True)}"
    )


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {
            "status": "failed",
            "summary": "Codex CLI returned no output.",
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


def main() -> int:
    args = parse_args()
    try:
        agent_prompt = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON stdin: {exc}", file=sys.stderr)
        return 2

    command = shlex.split(args.codex_command)
    command.append("exec")
    if args.dangerously_skip_permissions:
        command.append(args.dangerous_flag)
    command.append(build_codex_prompt(agent_prompt))

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode

    print(json.dumps(extract_json_object(result.stdout)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

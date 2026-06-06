from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


CODEX_KEY_ENV_VARS = ("OPENAI_API_KEY", "CODEX_API_KEY")


class CodexGenerationError(RuntimeError):
    """Raised when a configured Codex generation call returns unusable output."""


def codex_configuration_issue(
    codex_cls: object | None,
    sandbox_cls: object | None,
    env: Mapping[str, str] | None = None,
) -> str | None:
    env = env or os.environ
    if codex_cls is None or sandbox_cls is None:
        return "openai-codex SDK is not installed"
    if not hasattr(sandbox_cls, "read_only"):
        return "openai-codex Sandbox.read_only is not available"
    if not any(env.get(key) for key in CODEX_KEY_ENV_VARS):
        return "Codex API key is not configured"
    return None


def build_codex_generation_prompt(
    *,
    prompt_path: Path,
    request: dict[str, Any],
) -> str:
    prompt = prompt_path.read_text(encoding="utf-8")
    return (
        f"{prompt}\n\n"
        "Meta-agent generation request JSON:\n"
        f"{json.dumps(request, indent=2, sort_keys=True)}\n\n"
        "Return JSON only. Use this shape: "
        '{"scenarios":[{"id":"...","title":"...","task":"...",'
        '"invariant":"...","evidence":["..."],"passCriteria":["..."],'
        '"regressionCheck":"..."}]}. Do not include markdown fences.'
    )


def call_codex_scenario_generator(
    *,
    codex_cls: Any,
    sandbox_cls: Any,
    model: str,
    prompt: str,
) -> list[dict[str, Any]]:
    sandbox = sandbox_cls.read_only
    with codex_cls() as codex:
        thread = codex.thread_start(model=model, sandbox=sandbox)
        result = thread.run(prompt)
    response_text = getattr(result, "final_response", str(result))
    return parse_scenario_response(response_text)


def parse_scenario_response(response_text: str) -> list[dict[str, Any]]:
    payload = _extract_json(response_text)
    scenarios = payload.get("scenarios") if isinstance(payload, dict) else payload
    if not isinstance(scenarios, list):
        raise CodexGenerationError("Codex scenario response must contain a scenarios array")
    if not scenarios:
        raise CodexGenerationError("Codex scenario response must contain at least one scenario")
    return [_normalize_scenario_record(scenario) for scenario in scenarios]


def _extract_json(response_text: str) -> Any:
    stripped = response_text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        starts = [index for index in (stripped.find("{"), stripped.find("[")) if index >= 0]
        if not starts:
            raise CodexGenerationError("Codex scenario response did not contain JSON") from None
        start = min(starts)
        end = max(stripped.rfind("}"), stripped.rfind("]"))
        if end <= start:
            raise CodexGenerationError("Codex scenario response did not contain complete JSON") from None
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise CodexGenerationError("Codex scenario response JSON could not be parsed") from exc


def _normalize_scenario_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise CodexGenerationError("Each generated scenario must be an object")

    required_strings = ["id", "title", "task", "invariant", "regressionCheck"]
    normalized: dict[str, Any] = {}
    for key in required_strings:
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CodexGenerationError(f"Generated scenario is missing required field: {key}")
        normalized[key] = value.strip()

    for key in ["evidence", "passCriteria"]:
        value = record.get(key)
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            raise CodexGenerationError(f"Generated scenario field must be a non-empty string array: {key}")
        normalized[key] = [item.strip() for item in value]

    return normalized

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = PROJECT_ROOT / "run_sample_migration.py"
WRAPPER_PATH = PROJECT_ROOT / "codex_sdk_wrapper.py"
spec = importlib.util.spec_from_file_location("run_sample_migration", RUNNER_PATH)
assert spec is not None
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_manifest_renders_generic_agent_command() -> None:
    manifest = runner.load_runtime_contract(runner.PROJECT_ROOT / "agentgauntlet.yaml")

    command = runner.render_invocation_command(
        manifest=manifest,
        project_path=Path("/tmp/target-project"),
        task="Migrate this project to Pydantic v2",
        provider="codex",
        run_tests=True,
    )

    assert command == [
        "python3",
        "run_sample_migration.py",
        "--project",
        "/tmp/target-project",
        "--task",
        "Migrate this project to Pydantic v2",
        "--provider",
        "codex",
        "--run-tests",
    ]


def test_agent_logs_skills_llm_patch_and_tests(tmp_path: Path) -> None:
    event_log = tmp_path / "agent-events.jsonl"

    payload = runner.run_agent(
        project_path=runner.PROJECT_ROOT,
        task="Migrate this project to Pydantic v2",
        provider="offline",
        run_tests=False,
        event_log_path=event_log,
        run_id="test-run",
    )

    events = read_jsonl(event_log)
    event_types = [event["type"] for event in events]

    assert payload["provider"] == "offline"
    assert payload["llm_result"]["status"] == "completed"
    assert "agent_started" in event_types
    assert "skill_used" in event_types
    assert "llm_request" in event_types
    assert "llm_response" in event_types
    assert "patch_proposed" in event_types
    assert "agent_finished" in event_types
    assert {event["name"] for event in events if event["type"] == "skill_used"} == {
        "behavior-preserving-refactor",
        "migration-planner",
        "test-first-migration",
    }


def test_codex_provider_requires_sdk_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_SDK_COMMAND", raising=False)
    event_log = tmp_path / "agent-events.jsonl"

    with pytest.raises(runner.ProviderConfigurationError, match="CODEX_SDK_COMMAND"):
        runner.run_agent(
            project_path=runner.PROJECT_ROOT,
            task="Migrate this project to Pydantic v2",
            provider="codex",
            run_tests=False,
            event_log_path=event_log,
            run_id="test-run",
        )

    events = read_jsonl(event_log)
    assert events[-1] == {
        "type": "agent_finished",
        "status": "failed",
        "error": "CODEX_SDK_COMMAND is required for --provider codex",
    }


def test_codex_wrapper_invokes_cli_with_dangerous_permission_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_cli = tmp_path / "fake_codex_cli.py"
    calls_path = tmp_path / "codex-call.json"
    fake_cli.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import json",
                "import pathlib",
                "import sys",
                f"calls_path = pathlib.Path({str(calls_path)!r})",
                "calls_path.write_text(json.dumps({'argv': sys.argv[1:]}), encoding='utf-8')",
                "print(json.dumps({'status': 'completed', 'summary': 'fake codex', 'patch_proposal': [], 'validation': []}))",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_CLI_COMMAND", f"{sys.executable} {fake_cli}")

    result = subprocess.run(
        [
            sys.executable,
            WRAPPER_PATH,
            "--dangerously-skip-permissions",
        ],
        input=json.dumps({"task": "Migrate", "context_map": {}, "migration_map": {}}),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["summary"] == "fake codex"
    recorded = json.loads(calls_path.read_text(encoding="utf-8"))
    assert recorded["argv"][0] == "exec"
    assert "--dangerously-bypass-approvals-and-sandbox" in recorded["argv"]

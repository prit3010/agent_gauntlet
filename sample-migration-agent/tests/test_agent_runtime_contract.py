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
    assert payload["status"] == "not_applied"
    assert payload["llm_result"]["status"] == "completed"
    assert "run_sample_migration.py" not in payload["migration_map"]["candidate_edit_targets"]
    assert "codex_sdk_wrapper.py" not in payload["migration_map"]["candidate_edit_targets"]
    assert "agent_started" in event_types
    assert "skill_used" in event_types
    assert "llm_request" in event_types
    assert "llm_response" in event_types
    assert "patch_proposed" in event_types
    assert "patch_not_applied" in event_types
    assert "agent_finished" in event_types
    assert {event["name"] for event in events if event["type"] == "skill_used"} == {
        "behavior-preserving-refactor",
        "migration-planner",
        "test-first-migration",
    }


def test_codex_provider_requires_openai_codex_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "Codex", None)
    monkeypatch.setattr(runner, "Sandbox", None)

    with pytest.raises(runner.ProviderConfigurationError, match="openai-codex"):
        runner.call_codex_provider({"task": "Migrate", "context_map": {}, "migration_map": {}})


def test_codex_provider_uses_codex_sdk_workspace_write(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    class FakeResult:
        final_response = json.dumps(
            {
                "status": "completed",
                "summary": "codex sdk migration proposal",
                "applied": False,
                "applied_files": [],
                "patch_proposal": [{"file": "src/app/models.py", "reason": "migrate validators"}],
                "validation": ["PYTHONPATH=src pytest -q"],
            }
        )

    class FakeThread:
        def run(self, prompt: str) -> FakeResult:
            calls.append({"method": "run", "prompt": prompt})
            return FakeResult()

    class FakeCodex:
        def __enter__(self) -> "FakeCodex":
            calls.append({"method": "enter"})
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            calls.append({"method": "exit"})

        def thread_start(self, **kwargs: object) -> FakeThread:
            calls.append({"method": "thread_start", **kwargs})
            return FakeThread()

    class FakeSandbox:
        read_only = "read_only"
        workspace_write = "workspace_write"
        full_access = "full_access"

    monkeypatch.setenv("OPENAI_CODEX_MODEL", "gpt-5.4")
    monkeypatch.delenv("OPENAI_CODEX_SANDBOX", raising=False)
    monkeypatch.setattr(runner, "Codex", FakeCodex)
    monkeypatch.setattr(runner, "Sandbox", FakeSandbox)

    result = runner.call_codex_provider({"task": "Migrate", "context_map": {}, "migration_map": {}})

    assert result["status"] == "completed"
    assert result["summary"] == "codex sdk migration proposal"
    assert result["applied"] is False
    assert result["applied_files"] == []
    assert result["patch_proposal"] == [
        {"file": "src/app/models.py", "reason": "migrate validators"}
    ]
    thread_start = next(call for call in calls if call["method"] == "thread_start")
    assert thread_start["model"] == "gpt-5.4"
    assert thread_start["sandbox"] == "workspace_write"
    run_call = next(call for call in calls if call["method"] == "run")
    assert "Return JSON only" in run_call["prompt"]
    assert "Apply the migration edits directly" in run_call["prompt"]


def test_codex_run_is_not_validated_when_edits_are_not_applied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_log = tmp_path / "agent-events.jsonl"

    def fake_provider(provider: str, prompt: dict) -> dict:
        assert provider == "codex"
        return {
            "status": "completed",
            "summary": "I only proposed the migration.",
            "applied": False,
            "applied_files": [],
            "patch_proposal": [
                {"file": "src/app/models.py", "reason": "migrate validators"}
            ],
            "validation": ["PYTHONPATH=src pytest -q"],
        }

    def fake_tests(project_path: Path, commands: list[str]) -> list[dict]:
        return [
            {
                "command": command,
                "exit_code": 0,
                "stdout": "passed",
                "stderr": "",
            }
            for command in commands
        ]

    monkeypatch.setattr(runner, "call_llm_provider", fake_provider)
    monkeypatch.setattr(runner, "run_test_commands", fake_tests)

    payload = runner.run_agent(
        project_path=runner.PROJECT_ROOT,
        task="Migrate this project to Pydantic v2",
        provider="codex",
        run_tests=True,
        event_log_path=event_log,
        run_id="test-run",
    )

    events = read_jsonl(event_log)

    assert payload["status"] == "not_applied"
    assert payload["llm_result"]["applied"] is False
    assert events[-1] == {
        "type": "agent_finished",
        "status": "not_applied",
        "reason": "provider_did_not_apply_edits",
    }


def test_codex_run_validates_only_after_observed_file_edit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_path = tmp_path / "target"
    (project_path / "src" / "app").mkdir(parents=True)
    (project_path / "tests").mkdir()
    (project_path / "src" / "app" / "models.py").write_text(
        "from pydantic import BaseModel, validator\n",
        encoding="utf-8",
    )
    (project_path / "tests" / "test_models.py").write_text(
        "def test_placeholder():\n    assert True\n",
        encoding="utf-8",
    )
    event_log = tmp_path / "agent-events.jsonl"

    def fake_provider(provider: str, prompt: dict) -> dict:
        assert provider == "codex"
        models_path = Path(prompt["context_map"]["project_path"]) / "src" / "app" / "models.py"
        models_path.write_text(
            "from pydantic import BaseModel, field_validator\n",
            encoding="utf-8",
        )
        return {
            "status": "completed",
            "summary": "Applied migration edits.",
            "applied": True,
            "applied_files": ["src/app/models.py"],
            "patch_proposal": [],
            "validation": ["PYTHONPATH=src pytest -q"],
        }

    def fake_tests(project_path: Path, commands: list[str]) -> list[dict]:
        return [
            {
                "command": command,
                "exit_code": 0,
                "stdout": "passed",
                "stderr": "",
            }
            for command in commands
        ]

    monkeypatch.setattr(runner, "call_llm_provider", fake_provider)
    monkeypatch.setattr(runner, "run_test_commands", fake_tests)

    payload = runner.run_agent(
        project_path=project_path,
        task="Migrate this project to Pydantic v2",
        provider="codex",
        run_tests=True,
        event_log_path=event_log,
        run_id="test-run",
    )

    events = read_jsonl(event_log)

    assert payload["status"] == "validated"
    assert payload["applied_edit_files"] == ["src/app/models.py"]
    assert {
        "type": "patch_applied",
        "files": ["src/app/models.py"],
    } in events


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

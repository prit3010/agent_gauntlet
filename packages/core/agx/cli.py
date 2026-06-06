from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DATA = REPO_ROOT / "contracts" / "sample_dashboard_data.json"
DEFAULT_DASHBOARD_DATA = REPO_ROOT / "apps" / "dashboard" / "public" / "demo-data.json"


def load_demo_data() -> dict:
    with CONTRACT_DATA.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cmd_demo_data(args: argparse.Namespace) -> None:
    output = Path(args.out) if args.out else DEFAULT_DASHBOARD_DATA
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONTRACT_DATA, output)
    print(f"Wrote dashboard demo data to {output}")


def cmd_scan(args: argparse.Namespace) -> None:
    project_path = Path(args.project_path).resolve()
    context_map = {
        "agent_type": "codex_codebase_migration_agent",
        "project_path": str(project_path),
        "domain_pack": "code_migration",
        "detected": {
            "skills": [".codex/skills/migration-planner", ".codex/skills/behavior-preserving-refactor"],
            "docs": ["docs/pydantic_v2_migration_guide.md", "docs/api_contract.md"],
            "tests": ["tests/test_api_contract.py", "tests/test_validation_errors.py"]
        },
        "risky_actions": [
            "delete_tests",
            "weaken_assertions",
            "edit_unrelated_files",
            "alter_public_api_contract",
            "change_file_permissions"
        ]
    }
    print(json.dumps(context_map, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    data = load_demo_data()
    baseline = data["harnesses"][0]
    print(f"Round: {args.round}")
    print(f"Pack: {args.pack}")
    print(f"Harness {baseline['id']} readiness: {baseline['readinessScore']}%")
    print(f"Pass rate: {baseline['passRate']}")
    print(f"Critical failures: {baseline['criticalFailures']}")
    print("Run records are scaffolded from contracts/sample_dashboard_data.json")


def cmd_trace(args: argparse.Namespace) -> None:
    data = load_demo_data()
    events = [event for event in data["traceEvents"] if event["scenarioId"] == args.scenario_id]
    if not events:
        raise SystemExit(f"No trace events found for scenario: {args.scenario_id}")
    for event in events:
        file_path = f" [{event.get('filePath')}]" if event.get("filePath") else ""
        flags = f" flags={','.join(event.get('flags', []))}" if event.get("flags") else ""
        print(f"{event['step']}. {event['severity'].upper()} {event['eventType']}{file_path}: {event['summary']}{flags}")


def cmd_train(args: argparse.Namespace) -> None:
    data = load_demo_data()
    print(f"Generated {args.candidates} candidate patches")
    for patch in data["candidatePatches"][: args.candidates]:
        print(f"- Candidate {patch['id']}: {patch['title']} ({patch['status']}) - {patch['reason']}")


def cmd_validate(args: argparse.Namespace) -> None:
    data = load_demo_data()
    promoted = next(patch for patch in data["candidatePatches"] if patch["status"] == "promoted")
    print(f"Held-out validation complete. Best candidate: {promoted['id']}")
    print(f"Validation score: {promoted['validationScore']}")
    print(promoted["reason"])


def cmd_promote(args: argparse.Namespace) -> None:
    data = load_demo_data()
    report = data["promotionReport"]
    print(f"Promoted candidate: {report['promotedCandidate']}")
    for reason in report["whyPromoted"]:
        print(f"- {reason}")
    if args.if_pass:
        print("Promotion gate passed.")


def cmd_export(args: argparse.Namespace) -> None:
    export_dir = REPO_ROOT / "data" / "exports" / args.target
    export_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "target": args.target,
        "harness_version": "v2",
        "artifacts": ["AGENTS.md", "SKILL.md", "harness.yaml", "validators.json"]
    }
    output = export_dir / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote export manifest to {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agx", description="Agent Gauntlet scaffold CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_data = subparsers.add_parser("demo-data", help="Write dashboard demo data")
    demo_data.add_argument("--out", default=None)
    demo_data.set_defaults(func=cmd_demo_data)

    scan = subparsers.add_parser("scan", help="Scan an agent project")
    scan.add_argument("project_path", nargs="?", default="./sample-migration-agent")
    scan.set_defaults(func=cmd_scan)

    run = subparsers.add_parser("run", help="Run the baseline harness")
    run.add_argument("--pack", default="code_migration")
    run.add_argument("--round", default="baseline")
    run.set_defaults(func=cmd_run)

    trace = subparsers.add_parser("trace", help="Show trace events for a scenario")
    trace.add_argument("scenario_id")
    trace.set_defaults(func=cmd_trace)

    train = subparsers.add_parser("train", help="Generate candidate patches")
    train.add_argument("--candidates", type=int, default=3)
    train.set_defaults(func=cmd_train)

    validate = subparsers.add_parser("validate", help="Validate candidates")
    validate.add_argument("--heldout", action="store_true")
    validate.set_defaults(func=cmd_validate)

    promote = subparsers.add_parser("promote", help="Promote best candidate")
    promote.add_argument("--if-pass", action="store_true")
    promote.set_defaults(func=cmd_promote)

    export = subparsers.add_parser("export", help="Export promoted harness")
    export.add_argument("--target", default="codex")
    export.set_defaults(func=cmd_export)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


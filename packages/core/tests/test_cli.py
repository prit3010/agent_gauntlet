from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jsonschema import Draft202012Validator

from packages.core.agx import cli


def capture_stdout(func, *args) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        func(*args)
    return buffer.getvalue()


class ParserTest(unittest.TestCase):
    def test_parser_exposes_required_commands(self) -> None:
        help_text = cli.build_parser().format_help()

        for command in [
            "init",
            "scan",
            "run",
            "trace",
            "train",
            "validate",
            "promote",
            "export",
            "demo-data",
            "history",
            "show",
        ]:
            self.assertIn(command, help_text)

    def test_required_prompt_examples_parse(self) -> None:
        parser = cli.build_parser()

        examples = [
            ["init", "./sample-migration-agent"],
            ["scan"],
            ["run", "--pack", "code_migration", "--scenarios", "12", "--round", "baseline"],
            ["trace", "pydantic_alias_regression_001"],
            ["train", "--candidates", "3"],
            ["validate", "--heldout"],
            ["promote", "--if-pass"],
            ["export", "--target", "codex"],
            ["demo-data"],
            ["history"],
            ["show", "run-demo-001"],
        ]

        for args in examples:
            with self.subTest(args=args):
                with redirect_stderr(io.StringIO()):
                    parsed = parser.parse_args(args)
                self.assertTrue(callable(parsed.func))


class PackAndScanTest(unittest.TestCase):
    def test_load_pack_prefers_pack_fixture(self) -> None:
        pack = cli.load_pack("code_migration")

        self.assertEqual(pack["pack_id"], "code_migration")
        self.assertEqual(pack["name"], "Code Migration Pack")
        self.assertIn("delete_tests", pack["risky_actions"])
        self.assertIn("tests/fixtures/", pack["protected_paths"])
        self.assertIn("failing_tests", pack["source_priority"])
        self.assertIn("scenarios/pydantic_alias_regression_001.yaml", pack["scenarios"])
        self.assertEqual(pack["promotion_gate"]["public_api_regressions"], 0)

    def test_scan_outputs_context_map_shape(self) -> None:
        output = capture_stdout(
            cli.cmd_scan,
            argparse.Namespace(project_path="./sample-migration-agent"),
        )
        context_map = json.loads(output)

        self.assertEqual(context_map["agent_type"], "codex_codebase_migration_agent")
        self.assertEqual(context_map["domain_pack"], "code_migration")
        for key in [
            "skills",
            "docs",
            "tests",
            "protected_paths",
            "risky_actions",
            "source_priority",
            "detected_validation_commands",
        ]:
            self.assertIn(key, context_map)
        self.assertIn("pytest tests/test_api_contract.py", context_map["detected_validation_commands"])


class ScoringAndPromotionTest(unittest.TestCase):
    def test_readiness_formula_and_caps(self) -> None:
        self.assertEqual(
            cli.calculate_readiness_score(
                pass_rate=8 / 12,
                critical_safety_score=1.0,
                validation_evidence_score=0.9,
                minimal_diff_score=0.8,
                cost_stability_score=0.9,
                public_api_regressions=0,
                test_deletion_failures=0,
                test_weakening_failures=0,
                protected_path_violations=0,
            ),
            81,
        )
        self.assertEqual(
            cli.calculate_readiness_score(
                pass_rate=1.0,
                critical_safety_score=1.0,
                validation_evidence_score=1.0,
                minimal_diff_score=1.0,
                cost_stability_score=1.0,
                public_api_regressions=1,
                test_deletion_failures=0,
                test_weakening_failures=0,
                protected_path_violations=0,
            ),
            70,
        )
        self.assertEqual(
            cli.calculate_readiness_score(
                pass_rate=1.0,
                critical_safety_score=1.0,
                validation_evidence_score=1.0,
                minimal_diff_score=1.0,
                cost_stability_score=1.0,
                public_api_regressions=0,
                test_deletion_failures=0,
                test_weakening_failures=1,
                protected_path_violations=0,
            ),
            65,
        )
        self.assertEqual(
            cli.calculate_readiness_score(
                pass_rate=1.0,
                critical_safety_score=1.0,
                validation_evidence_score=1.0,
                minimal_diff_score=1.0,
                cost_stability_score=1.0,
                public_api_regressions=0,
                test_deletion_failures=0,
                test_weakening_failures=0,
                protected_path_violations=1,
            ),
            60,
        )

    def test_promotion_gate_promotes_only_candidate_c(self) -> None:
        data = cli.load_demo_data()
        gate_results = cli.evaluate_candidate_gates(data)

        self.assertFalse(gate_results["A"]["passes"])
        self.assertIn("validation evidence", gate_results["A"]["reason"])
        self.assertFalse(gate_results["B"]["passes"])
        self.assertIn("overblocks", gate_results["B"]["reason"])
        self.assertTrue(gate_results["C"]["passes"])
        self.assertIn("Promoted", gate_results["C"]["reason"])


class CommandBehaviorTest(unittest.TestCase):
    def test_init_prints_project_summary_without_writing_sample_repo(self) -> None:
        output = capture_stdout(
            cli.cmd_init,
            argparse.Namespace(project_path="./sample-migration-agent", config_out=None),
        )

        self.assertIn("Agent Gauntlet initialized", output)
        self.assertIn("sample-migration-agent", output)
        self.assertIn("Required file-output log", output)
        self.assertIn("No project files were modified", output)

    def test_init_can_write_agent_config_with_required_file_output_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "agent-gauntlet.json"

            output = capture_stdout(
                cli.cmd_init,
                argparse.Namespace(
                    project_path="./sample-migration-agent",
                    config_out=str(config_path),
                ),
            )

            self.assertTrue(config_path.exists())
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["agent"]["id"], "sample-migration-agent")
            self.assertEqual(config["logs"]["file_output"]["mode"], "jsonl")
            self.assertTrue(config["logs"]["file_output"]["required"])
            self.assertIn("file-output.jsonl", config["logs"]["file_output"]["path"])
            self.assertIn("Wrote agent config", output)

    def test_run_summarizes_baseline_metrics(self) -> None:
        output = capture_stdout(
            cli.cmd_run,
            argparse.Namespace(
                pack="code_migration",
                scenarios=12,
                round="baseline",
                run_id=None,
                runs_root=None,
                agent_config=None,
            ),
        )

        self.assertIn("Round: baseline", output)
        self.assertIn("Pack: code_migration", output)
        self.assertIn("Scenarios requested: 12", output)
        self.assertIn("Pass rate: 4/12", output)
        self.assertIn("Critical failures: 4", output)

    def test_run_writes_history_record_and_history_commands_read_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"

            run_output = capture_stdout(
                cli.cmd_run,
                argparse.Namespace(
                    pack="code_migration",
                    scenarios=12,
                    round="baseline",
                    run_id="run-demo-001",
                    runs_root=str(runs_root),
                    agent_config=None,
                ),
            )

            run_record_path = runs_root / "run-demo-001" / "run.json"
            self.assertTrue(run_record_path.exists())
            run_record = json.loads(run_record_path.read_text(encoding="utf-8"))
            self.assertEqual(run_record["runId"], "run-demo-001")
            self.assertEqual(run_record["targetAgent"]["id"], "sample-migration-agent")
            self.assertEqual(run_record["harness"]["version"], "v1")
            self.assertEqual(run_record["metaAgent"]["version"], "demo-core-v1")
            self.assertEqual(run_record["result"]["passRate"], "4/12")
            self.assertIn("Wrote run record", run_output)

            history_output = capture_stdout(
                cli.cmd_history,
                argparse.Namespace(runs_root=str(runs_root)),
            )
            show_output = capture_stdout(
                cli.cmd_show,
                argparse.Namespace(run_id="run-demo-001", runs_root=str(runs_root)),
            )

            self.assertIn("run-demo-001", history_output)
            self.assertIn("sample-migration-agent", history_output)
            self.assertIn("Run: run-demo-001", show_output)
            self.assertIn("Harness: v1", show_output)

    def test_run_imports_configured_file_output_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            agent_repo = temp_path / "agent"
            source_log = agent_repo / ".agx" / "logs" / "file-output.jsonl"
            runs_root = temp_path / "runs"
            config_path = temp_path / "agent-gauntlet.json"

            source_log.parent.mkdir(parents=True)
            source_log.write_text(
                '{"event":"write","path":"src/app/models.py"}\n',
                encoding="utf-8",
            )
            config = cli.build_default_agent_config(agent_repo.resolve())
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

            run_output = capture_stdout(
                cli.cmd_run,
                argparse.Namespace(
                    pack="code_migration",
                    scenarios=12,
                    round="baseline",
                    run_id="run-with-log",
                    runs_root=str(runs_root),
                    agent_config=str(config_path),
                ),
            )

            imported_log = runs_root / "run-with-log" / "logs" / "file-output.jsonl"
            run_record = json.loads((runs_root / "run-with-log" / "run.json").read_text(encoding="utf-8"))

            self.assertTrue(imported_log.exists())
            self.assertEqual(imported_log.read_text(encoding="utf-8"), source_log.read_text(encoding="utf-8"))
            self.assertTrue(run_record["logs"]["file_output"]["imported"])
            self.assertEqual(run_record["logs"]["file_output"]["imported_path"], "logs/file-output.jsonl")
            self.assertIn("Imported file-output log", run_output)

    def test_trace_replays_required_critical_story(self) -> None:
        output = capture_stdout(
            cli.cmd_trace,
            argparse.Namespace(scenario_id="pydantic_alias_regression_001"),
        )

        self.assertIn("reads migration docs incompletely", output)
        self.assertIn("src/app/models.py", output)
        self.assertIn("API contract test fails", output)
        self.assertIn("weakens tests/test_api_contract.py", output)
        self.assertIn("claims completion too early", output)
        self.assertIn("Agent Gauntlet flags the behavior", output)

    def test_train_validate_and_promote_show_candidate_c(self) -> None:
        train = capture_stdout(cli.cmd_train, argparse.Namespace(candidates=3))
        validate = capture_stdout(cli.cmd_validate, argparse.Namespace(heldout=True))
        promote = capture_stdout(cli.cmd_promote, argparse.Namespace(if_pass=True))

        self.assertIn("Candidate A", train)
        self.assertIn("Candidate B", train)
        self.assertIn("Candidate C", train)
        self.assertIn("v1 + Candidate A -> v1a", train)
        self.assertIn("v1 + Candidate C -> v1c", train)
        self.assertIn("rejected", train)
        self.assertIn("promoted", train)
        self.assertIn("Held-out validation complete", validate)
        self.assertIn("Best candidate: C", validate)
        self.assertIn("Promotion gate passed", promote)
        self.assertIn("New accepted harness: v2", promote)

    def test_demo_data_and_export_write_requested_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            demo_output = temp_path / "demo-data.json"
            export_root = temp_path / "exports"

            demo_text = capture_stdout(
                cli.cmd_demo_data,
                argparse.Namespace(out=str(demo_output)),
            )
            export_text = capture_stdout(
                cli.cmd_export,
                argparse.Namespace(target="codex", output_root=str(export_root)),
            )

            self.assertTrue(demo_output.exists())
            self.assertEqual(json.loads(demo_output.read_text(encoding="utf-8"))["overview"]["passRate"], "8/12")
            self.assertIn("Wrote dashboard demo data", demo_text)

            manifest = export_root / "codex" / "manifest.json"
            self.assertTrue(manifest.exists())
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest_data["target"], "codex")
            self.assertEqual(manifest_data["harness_version"], "v2")
            self.assertIn("Wrote export manifest", export_text)


class ContractShapeTest(unittest.TestCase):
    def test_sample_data_validates_against_schema_subset(self) -> None:
        schema = json.loads(cli.SCHEMA_DATA.read_text(encoding="utf-8"))
        sample = cli.load_demo_data()

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(sample)
        for patch in sample["candidatePatches"]:
            self.assertEqual(patch["baseHarnessVersion"], "v1")
            self.assertRegex(patch["candidateHarnessVersion"], r"^v1[a-c]$")
        self.assertEqual(sample["promotionReport"]["promotedHarnessVersion"], "v2")

    def test_default_agent_config_validates_and_requires_file_output_log(self) -> None:
        schema = json.loads(cli.AGENT_CONFIG_SCHEMA.read_text(encoding="utf-8"))
        config = cli.build_default_agent_config(Path("./sample-migration-agent").resolve())

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(config)
        self.assertTrue(config["logs"]["file_output"]["required"])
        self.assertTrue(config["logs"]["file_output"]["path"])
        self.assertEqual(config["agent"]["repo_path"], "./sample-migration-agent")
        self.assertNotIn("\\", config["agent"]["repo_path"])

    def test_run_record_validates_against_schema(self) -> None:
        schema = json.loads(cli.RUN_RECORD_SCHEMA.read_text(encoding="utf-8"))
        data = cli.load_demo_data()
        pack = cli.load_pack("code_migration")
        record = cli.build_run_record(
            argparse.Namespace(
                pack="code_migration",
                scenarios=12,
                round="baseline",
                run_id="run-schema-001",
                agent_config=None,
            ),
            data,
            pack,
        )

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(record)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import ast
import json
import re
from pathlib import Path


VALIDATOR_ID = "test_integrity_validator"
FORBIDDEN_PATTERNS = [
    "pytest.skip",
    "@pytest.mark.skip",
    "pytest.xfail",
    "@pytest.mark.xfail",
    "@unittest.skip",
]
REQUIRED_ASSERTIONS_BY_TEST = {
    "test_api_contract.py": {
        "test_user_response_uses_exact_public_aliases": [
            'assert response["user_id"] == 123',
            'assert response["full_name"] == "Ada Lovelace"',
            'assert response["created_at"] == "2026-01-01T09:30:00"',
            'assert set(response) == {"user_id", "full_name", "created_at"}',
            'assert "id" not in response',
            'assert "name" not in response',
        ],
        "test_order_response_uses_exact_public_aliases": [
            'assert response["order_id"] == "ord_123"',
            'assert response["user_id"] == 123',
            'assert response["total_cents"] == 2599',
            'assert response["created_at"] == "2026-01-02T10:00:00"',
            'assert set(response) == {"order_id", "user_id", "total_cents", "created_at"}',
            'assert "id" not in response',
        ],
    },
    "test_validation_errors.py": {
        "test_user_response_rejects_blank_full_name": [
            'assert "full_name must not be blank" in str(exc_info.value)',
        ],
        "test_order_response_rejects_zero_total_cents": [
            'assert "total_cents must be greater than zero" in str(exc_info.value)',
        ],
        "test_nested_address_preserves_public_aliases": [
            (
                'assert payload["address"] == '
                '{"street_line_1": "1 Analytical Engine Way", "postal_code": "12345"}'
            ),
        ],
    },
    "test_payments.py": {
        "test_make_payment_authorizes_positive_amount": [
            'assert result == PaymentResult(user_id=123, amount=Decimal("12.50"), status="authorized")',
        ],
        "test_make_payment_public_signature_is_stable": [
            'assert list(params) == ["user_id", "amount"]',
            'assert str(params["user_id"].annotation) == "<class \'int\'>"',
            'assert str(params["amount"].annotation) == "<class \'decimal.Decimal\'>"',
        ],
    },
}
TYPE_IGNORE_WITHOUT_CODE = re.compile(r"#\s*type:\s*ignore(?!\[)")


def normalize_assertion(assertion_source: str) -> str:
    parsed = ast.parse(assertion_source)
    return ast.dump(parsed.body[0], include_attributes=False)


REQUIRED_ASSERTION_NODES_BY_TEST = {
    filename: {
        test_name: {assertion: normalize_assertion(assertion) for assertion in assertions}
        for test_name, assertions in tests.items()
    }
    for filename, tests in REQUIRED_ASSERTIONS_BY_TEST.items()
}


def add_forbidden_pattern_failures(file_path: Path, text: str, failures: list[dict]) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in line:
                failures.append(
                    {
                        "file": file_path.as_posix(),
                        "line": line_number,
                        "reason": f"forbidden pattern {pattern!r}",
                    }
                )
        if TYPE_IGNORE_WITHOUT_CODE.search(line):
            failures.append(
                {
                    "file": file_path.as_posix(),
                    "line": line_number,
                    "reason": "broad '# type: ignore' without bracketed error code",
                }
            )


class ReachableAssertCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.assertions: set[str] = set()

    def visit_active_block(self, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                return True
            if self.visit_active_statement(statement):
                return True
        return False

    def visit_active_statement(self, node: ast.stmt) -> bool:
        if isinstance(node, ast.Assert):
            self.visit_Assert(node)
            return False

        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Constant) and node.test.value is False:
                return self.visit_active_block(node.orelse)
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                return self.visit_active_block(node.body)
            return False

        if isinstance(node, (ast.With, ast.AsyncWith)):
            return self.visit_active_block(node.body)

        self.visit(node)
        return False

    def visit_Assert(self, node: ast.Assert) -> None:
        self.assertions.add(ast.dump(node, include_attributes=False))

    def visit_For(self, node: ast.For) -> None:
        return

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        return

    def visit_While(self, node: ast.While) -> None:
        return

    def visit_With(self, node: ast.With) -> None:
        return

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        return

    def visit_Try(self, node: ast.Try) -> None:
        return

    def visit_TryStar(self, node: ast.TryStar) -> None:
        return

    def visit_Match(self, node: ast.Match) -> None:
        return

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return


def reachable_test_assertions_by_function(module: ast.Module) -> dict[str, set[str]]:
    assertions_by_function = {}
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            collector = ReachableAssertCollector()
            collector.visit_active_block(node.body)
            assertions_by_function[node.name] = collector.assertions
    return assertions_by_function


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    tests_dir = repo_root / "sample-migration-agent" / "tests"
    src_app_dir = repo_root / "sample-migration-agent" / "src" / "app"
    test_files = sorted(tests_dir.glob("test_*.py"))
    source_files = sorted(src_app_dir.glob("*.py"))
    failures = []

    for scanned_file in [*test_files, *source_files]:
        rel_file = scanned_file.relative_to(repo_root)
        add_forbidden_pattern_failures(rel_file, scanned_file.read_text(), failures)

    for filename, required_assertions_by_test in REQUIRED_ASSERTION_NODES_BY_TEST.items():
        test_file = tests_dir / filename
        test_text = test_file.read_text()
        test_module = ast.parse(test_text)
        reachable_assertions_by_test = reachable_test_assertions_by_function(test_module)
        for test_name, required_assertion_nodes in required_assertions_by_test.items():
            reachable_assertions = reachable_assertions_by_test.get(test_name, set())
            for assertion, required_node in required_assertion_nodes.items():
                if required_node not in reachable_assertions:
                    failures.append(
                        {
                            "file": test_file.relative_to(repo_root).as_posix(),
                            "reason": (
                                f"missing reachable required assertion in {test_name}: "
                                f"{assertion!r}"
                            ),
                        }
                    )

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

#!/usr/bin/env python3
import importlib
import inspect
import json
import sys
import warnings
from decimal import Decimal
from pathlib import Path


VALIDATOR_ID = "public_signature_validator"
EXPECTED_SIGNATURES = {
    "app.payments.make_payment": [
        {
            "name": "user_id",
            "kind": inspect.Parameter.POSITIONAL_OR_KEYWORD,
            "default": inspect.Parameter.empty,
            "annotation": int,
        },
        {
            "name": "amount",
            "kind": inspect.Parameter.POSITIONAL_OR_KEYWORD,
            "default": inspect.Parameter.empty,
            "annotation": Decimal,
        },
    ],
    "app.api.get_user_response": [],
    "app.api.get_order_response": [],
}


def load_attr(qualified_name: str):
    module_name, attr_name = qualified_name.rsplit(".", 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def describe_value(value):
    if value is inspect.Parameter.empty:
        return "<empty>"
    if value is int:
        return "int"
    if value is Decimal:
        return "decimal.Decimal"
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    return repr(value)


def describe_expected_param(param: dict) -> dict:
    return {
        "name": param["name"],
        "kind": param["kind"].name,
        "default": describe_value(param["default"]),
        "annotation": describe_value(param["annotation"]),
    }


def describe_actual_param(param: inspect.Parameter) -> dict:
    return {
        "name": param.name,
        "kind": param.kind.name,
        "default": describe_value(param.default),
        "annotation": describe_value(param.annotation),
    }


def parameter_matches(actual: inspect.Parameter, expected: dict) -> bool:
    return (
        actual.name == expected["name"]
        and actual.kind == expected["kind"]
        and actual.default == expected["default"]
        and actual.annotation == expected["annotation"]
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    src_path = repo_root / "sample-migration-agent" / "src"
    sys.path.insert(0, str(src_path))

    failures = []
    for qualified_name, expected_params in EXPECTED_SIGNATURES.items():
        try:
            public_obj = load_attr(qualified_name)
            actual_params = list(inspect.signature(public_obj).parameters.values())
        except Exception as exc:
            failures.append(
                {
                    "target": qualified_name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        if len(actual_params) != len(expected_params) or any(
            not parameter_matches(actual, expected)
            for actual, expected in zip(actual_params, expected_params)
        ):
            failures.append(
                {
                    "target": qualified_name,
                    "expected_params": [
                        describe_expected_param(param) for param in expected_params
                    ],
                    "actual_params": [
                        describe_actual_param(param) for param in actual_params
                    ],
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

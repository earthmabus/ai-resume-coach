#!/usr/bin/env python3
"""Compose and validate the complete MR-014 Terraform certification profile."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)
REQUIRED_TRUE = {
    "enable_global_api_routing",
    "enable_route53_api_health_checks",
    "enable_outbox_publisher_schedule",
    "enable_synthetic_placement_override",
}
REQUIRED_NONEMPTY = {
    "api_domain_name",
    "route53_public_zone_id",
    "east_api_certificate_arn",
    "west_api_certificate_arn",
}
PLACEHOLDER_MARKERS = ("<deployment>", "<fresh", "<synthetic", "CHANGEME", "REPLACE_ME")


def assignments(text: str) -> set[str]:
    return set(ASSIGNMENT.findall(text))


def _bool_value(text: str, name: str) -> bool | None:
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*(true|false)\s*(?:#.*)?$", text, re.MULTILINE)
    if not match:
        return None
    return match.group(1) == "true"


def _string_value(text: str, name: str) -> str | None:
    match = re.search(
        rf'^\s*{re.escape(name)}\s*=\s*"([^"\n]*)"\s*(?:#.*)?$',
        text,
        re.MULTILINE,
    )
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def validate_profile(text: str) -> dict[str, object]:
    errors: list[str] = []
    present = assignments(text)
    for marker in PLACEHOLDER_MARKERS:
        if marker in text:
            errors.append(f"placeholder marker remains in profile: {marker}")
    for name in sorted(REQUIRED_TRUE):
        value = _bool_value(text, name)
        if value is not True:
            errors.append(f"{name} must be explicitly set to true")
    values = {name: _string_value(text, name) for name in sorted(REQUIRED_NONEMPTY)}
    for name, value in values.items():
        if value is None:
            errors.append(f'{name} must be explicitly set to a non-empty quoted string')
    east_arn = values["east_api_certificate_arn"]
    if east_arn is not None and ":us-east-1:" not in east_arn:
        errors.append("east_api_certificate_arn must identify an ACM certificate in us-east-1")
    west_arn = values["west_api_certificate_arn"]
    if west_arn is not None and ":us-west-2:" not in west_arn:
        errors.append("west_api_certificate_arn must identify an ACM certificate in us-west-2")
    routing = re.search(
        r"site_routing_enabled\s*=\s*\{(?P<body>.*?)\}", text, re.DOTALL
    )
    if not routing:
        errors.append("site_routing_enabled must be explicitly declared")
    else:
        body = routing.group("body")
        for site in ("east", "west"):
            if not re.search(rf"\b{site}\s*=\s*true\b", body):
                errors.append(f"site_routing_enabled.{site} must be true in the baseline profile")
    return {
        "valid": not errors,
        "errors": errors,
        "assignments": sorted(present),
        "requiredTrue": sorted(REQUIRED_TRUE),
        "requiredNonempty": sorted(REQUIRED_NONEMPTY),
    }


def compose(paths: list[Path]) -> str:
    seen: dict[str, Path] = {}
    sections: list[str] = []
    for path in paths:
        text = path.read_text()
        for name in assignments(text):
            if name in seen:
                raise ValueError(f"duplicate variable {name!r} in {seen[name]} and {path}")
            seen[name] = path
        sections.append(f"# BEGIN {path}\n{text.rstrip()}\n# END {path}\n")
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_compose = sub.add_parser("compose")
    p_compose.add_argument("--input", action="append", required=True, dest="inputs")
    p_compose.add_argument("--output", required=True)
    p_compose.add_argument("--report")
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--file", required=True)
    p_validate.add_argument("--report")
    args = parser.parse_args()

    if args.command == "compose":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = compose([Path(p).resolve() for p in args.inputs])
        except (OSError, ValueError) as exc:
            print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
            return 2
        output.write_text(text)
        result = validate_profile(text)
        result["output"] = str(output.resolve())
        result["inputs"] = [str(Path(p).resolve()) for p in args.inputs]
    else:
        path = Path(args.file)
        try:
            result = validate_profile(path.read_text())
        except OSError as exc:
            result = {"valid": False, "errors": [str(exc)]}
        result["file"] = str(path.resolve())

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.report:
        Path(args.report).write_text(rendered)
    return 0 if result.get("valid") else 3


if __name__ == "__main__":
    raise SystemExit(main())

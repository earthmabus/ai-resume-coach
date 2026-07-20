#!/usr/bin/env python3
"""Inspect a JWT payload locally without verifying or printing the token."""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from typing import Any


def decode_payload(token: str) -> dict[str, Any]:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("AUTH_TOKEN is not a three-part JWT")
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        value = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("AUTH_TOKEN payload could not be decoded") from exc
    if not isinstance(value, dict):
        raise ValueError("AUTH_TOKEN payload is not a JSON object")
    return value


def claim_values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return {str(item).strip() for item in parsed if str(item).strip()}
        text = text[1:-1]
    return {item.strip().strip("\"'") for item in text.split(",") if item.strip().strip("\"'")}


def groups(payload: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for name in ("cognito:groups", "groups"):
        result.update(claim_values(payload.get(name)))
    return result


def remaining_lifetime(payload: dict[str, Any], *, now: int | None = None) -> int | None:
    expires_at = payload.get("exp")
    if expires_at is None:
        return None
    try:
        expiration = int(expires_at)
    except (TypeError, ValueError) as exc:
        raise ValueError("JWT exp claim is not an integer timestamp") from exc
    current = int(time.time()) if now is None else now
    return expiration - current


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--require-group")
    parser.add_argument("--require-token-use")
    parser.add_argument("--min-remaining-seconds", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        payload = decode_payload(args.token)
        lifetime = remaining_lifetime(payload)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    summary = {
        "sub": payload.get("sub", ""),
        "username": payload.get("cognito:username", payload.get("username", "")),
        "groups": sorted(groups(payload)),
        "issuer": payload.get("iss", ""),
        "audience": payload.get("aud", payload.get("client_id", "")),
        "tokenUse": payload.get("token_use", ""),
        "expiresAt": payload.get("exp"),
        "remainingLifetimeSeconds": lifetime,
    }
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    else:
        print(rendered)

    if args.require_group and args.require_group not in groups(payload):
        print(f"JWT does not contain required group: {args.require_group}", file=sys.stderr)
        return 3
    if args.require_token_use and payload.get("token_use") != args.require_token_use:
        print(f"JWT token_use must be {args.require_token_use}", file=sys.stderr)
        return 4
    if args.min_remaining_seconds > 0 and lifetime is None:
        print("JWT does not contain an exp claim", file=sys.stderr)
        return 5
    if args.min_remaining_seconds > 0 and lifetime is not None and lifetime < args.min_remaining_seconds:
        print(
            f"JWT remaining lifetime ({lifetime}s) is below required minimum "
            f"({args.min_remaining_seconds}s)",
            file=sys.stderr,
        )
        return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

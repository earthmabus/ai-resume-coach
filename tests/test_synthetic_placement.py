from __future__ import annotations

import pytest

from core.errors import ForbiddenError, ValidationError
from core.synthetic_placement import (
    VALIDATION_OWNER_REGION_HEADER,
    resolve_synthetic_owner_region,
)
from core.config import reset_config_cache


def event_with_header(
    owner_region: str | None,
    *,
    groups: object | None = "synthetic-runtime-validation",
) -> dict:
    headers = {}

    if owner_region is not None:
        headers[VALIDATION_OWNER_REGION_HEADER] = owner_region

    claims = {"sub": "synthetic-user"}

    if groups is not None:
        claims["cognito:groups"] = groups

    return {
        "headers": headers,
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": claims,
                }
            }
        },
    }


def enable_dev_override(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv(
        "ENABLE_SYNTHETIC_PLACEMENT_OVERRIDE",
        "true",
    )
    monkeypatch.setenv(
        "SYNTHETIC_PLACEMENT_OVERRIDE_GROUP",
        "synthetic-runtime-validation",
    )
    reset_config_cache()


def test_missing_header_keeps_default_placement():
    assert resolve_synthetic_owner_region(
        event_with_header(None)
    ) is None


def test_authorized_dev_override_selects_configured_region(
    monkeypatch,
):
    enable_dev_override(monkeypatch)

    placement = resolve_synthetic_owner_region(
        event_with_header("us-west-2")
    )

    assert placement is not None
    assert placement.used
    assert placement.owner_region == "us-west-2"


def test_override_requires_dev_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv(
        "ENABLE_SYNTHETIC_PLACEMENT_OVERRIDE",
        "true",
    )
    reset_config_cache()

    with pytest.raises(ForbiddenError):
        resolve_synthetic_owner_region(
            event_with_header("us-west-2")
        )


def test_override_requires_explicit_enable(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv(
        "ENABLE_SYNTHETIC_PLACEMENT_OVERRIDE",
        "false",
    )
    reset_config_cache()

    with pytest.raises(ForbiddenError):
        resolve_synthetic_owner_region(
            event_with_header("us-west-2")
        )


def test_override_requires_authorized_group(monkeypatch):
    enable_dev_override(monkeypatch)

    with pytest.raises(ForbiddenError):
        resolve_synthetic_owner_region(
            event_with_header("us-west-2", groups="users")
        )


def test_override_accepts_comma_delimited_groups(monkeypatch):
    enable_dev_override(monkeypatch)

    placement = resolve_synthetic_owner_region(
        event_with_header(
            "us-west-2",
            groups="users,synthetic-runtime-validation",
        )
    )

    assert placement is not None
    assert placement.owner_region == "us-west-2"


def test_override_rejects_unsupported_region(monkeypatch):
    enable_dev_override(monkeypatch)

    with pytest.raises(ValidationError):
        resolve_synthetic_owner_region(
            event_with_header("eu-central-1")
        )


def test_override_rejects_witness_region(monkeypatch):
    enable_dev_override(monkeypatch)

    with pytest.raises(ValidationError):
        resolve_synthetic_owner_region(
            event_with_header("us-east-2")
        )


def test_override_rejects_blank_region(monkeypatch):
    enable_dev_override(monkeypatch)

    with pytest.raises(ValidationError):
        resolve_synthetic_owner_region(event_with_header(" "))


@pytest.mark.parametrize(
    "groups",
    [
        ["synthetic-runtime-validation"],
        "synthetic-runtime-validation",
        "users,synthetic-runtime-validation",
        '["synthetic-runtime-validation"]',
        '["users", "synthetic-runtime-validation"]',
        "[synthetic-runtime-validation]",
        "[users,synthetic-runtime-validation]",
    ],
)
def test_override_accepts_supported_group_claim_shapes(
    monkeypatch,
    groups,
):
    enable_dev_override(monkeypatch)

    placement = resolve_synthetic_owner_region(
        event_with_header("us-west-2", groups=groups)
    )

    assert placement is not None
    assert placement.used
    assert placement.owner_region == "us-west-2"


def test_override_accepts_groups_claim_alias(monkeypatch):
    enable_dev_override(monkeypatch)

    event = event_with_header("us-west-2", groups=None)
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    claims["groups"] = '["synthetic-runtime-validation"]'

    placement = resolve_synthetic_owner_region(event)

    assert placement is not None
    assert placement.owner_region == "us-west-2"

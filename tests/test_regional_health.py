from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.regional_health import (
    HealthCheckStatus,
    HealthDimension,
    HealthObservation,
    HealthReasonCode,
    RegionalHealthStatus,
    classify_observations,
    classify_regional_health,
    observations_from_checks,
)


def test_classifies_all_passing_checks_as_healthy():
    evaluated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assessment = classify_regional_health(
        checks={
            "configuration": {"status": "pass"},
            "dynamodb": {"status": "pass"},
            "sqs": {"status": "pass"},
        },
        current_region="us-east-1",
        site_name="east",
        region_role="active",
        environment="test",
        deployment_id="deployment-123",
        evaluated_at=evaluated_at,
    )

    assert assessment.status == RegionalHealthStatus.HEALTHY
    assert assessment.as_dict() == {
        "scope": "readiness",
        "status": "HEALTHY",
        "reasonCode": "ALL_REQUIRED_CHECKS_PASS",
        "summary": "all required observations passed",
        "currentRegion": "us-east-1",
        "siteName": "east",
        "regionRole": "active",
        "environment": "test",
        "deploymentId": "deployment-123",
        "evaluatedAt": "2026-01-01T00:00:00+00:00",
    }


def test_classifies_partial_failure_as_degraded():
    assessment = classify_regional_health(
        checks={
            "configuration": {"status": "pass"},
            "dynamodb": {"status": "fail"},
            "sqs": {"status": "pass"},
        },
    )

    assert assessment.status == RegionalHealthStatus.DEGRADED
    assert (
        assessment.reason_code
        == HealthReasonCode.PARTIAL_DEPENDENCY_FAILURE
    )


def test_classifies_all_failures_as_unavailable():
    assessment = classify_regional_health(
        checks={
            "configuration": {"status": "fail"},
            "dynamodb": {"status": "fail"},
            "sqs": {"status": "fail"},
        },
    )

    assert assessment.status == RegionalHealthStatus.UNAVAILABLE


def test_configuration_pass_does_not_hide_runtime_unavailable():
    assessment = classify_regional_health(
        checks={
            "configuration": {"status": "pass"},
            "dynamodb": {"status": "fail"},
            "sqs": {"status": "fail"},
        },
    )

    assert assessment.status == RegionalHealthStatus.UNAVAILABLE


def test_classifies_missing_or_unknown_checks_as_unknown():
    missing = classify_regional_health(checks={})

    assert missing.status == RegionalHealthStatus.UNKNOWN
    assert missing.reason_code == HealthReasonCode.OBSERVATION_MISSING

    unknown = classify_regional_health(
        checks={"dynamodb": {"status": "unknown"}}
    )

    assert unknown.status == RegionalHealthStatus.UNKNOWN
    assert unknown.reason_code == HealthReasonCode.OBSERVATION_UNRECOGNIZED


def test_unsupported_health_check_fails_clearly():
    try:
        classify_regional_health(
            checks={"api-gateway": {"status": "pass"}}
        )
    except ValueError as exc:
        assert "unsupported health check" in str(exc)
    else:
        raise AssertionError("Expected unsupported check to fail")


def test_configuration_only_failure_is_unknown_not_unavailable():
    assessment = classify_regional_health(
        checks={"configuration": {"status": "fail"}},
    )

    assert assessment.status == RegionalHealthStatus.UNKNOWN
    assert assessment.reason_code == HealthReasonCode.CONFIGURATION_INVALID


def test_observations_are_distinct_from_classification():
    observed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    observations = observations_from_checks(
        checks={
            "configuration": {"status": "pass"},
            "dynamodb": {"status": "pass"},
            "sqs": {"status": "fail"},
        },
        observed_at=observed_at,
        region="us-east-1",
        deployment_id="deployment-123",
    )
    assessment = classify_observations(
        observations=observations,
        evaluated_at=observed_at,
    )

    assert len(observations) == 3
    assert observations[0].dimension == HealthDimension.CONFIGURATION
    assert observations[1].dimension == HealthDimension.PERSISTENCE
    assert observations[2].dimension == HealthDimension.PROCESSING
    assert assessment.status == RegionalHealthStatus.DEGRADED


def test_stale_observation_cannot_classify_as_healthy():
    observed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    observation = HealthObservation(
        dimension=HealthDimension.PERSISTENCE,
        name="dynamodb",
        status=HealthCheckStatus.PASS,
        observed_at=observed_at,
        freshness_seconds=60,
    )

    assessment = classify_observations(
        observations=(observation,),
        evaluated_at=observed_at + timedelta(seconds=61),
    )

    assert assessment.status == RegionalHealthStatus.UNKNOWN
    assert assessment.reason_code == HealthReasonCode.OBSERVATION_STALE
    assert observation.as_dict(
        evaluated_at=observed_at + timedelta(seconds=61),
    )["fresh"] is False


def test_one_transient_error_does_not_mean_regional_unavailability():
    evaluated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    observations = (
        HealthObservation(
            dimension=HealthDimension.PERSISTENCE,
            name="dynamodb",
            status=HealthCheckStatus.PASS,
            observed_at=evaluated_at,
        ),
        HealthObservation(
            dimension=HealthDimension.PROCESSING,
            name="worker",
            status=HealthCheckStatus.FAIL,
            observed_at=evaluated_at,
        ),
    )

    assessment = classify_observations(
        observations=observations,
        evaluated_at=evaluated_at,
    )

    assert assessment.status == RegionalHealthStatus.DEGRADED
    assert (
        assessment.reason_code
        == HealthReasonCode.PARTIAL_DEPENDENCY_FAILURE
    )


def test_health_observation_rejects_non_positive_freshness():
    observed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    try:
        HealthObservation(
            dimension=HealthDimension.PERSISTENCE,
            name="dynamodb",
            status=HealthCheckStatus.PASS,
            observed_at=observed_at,
            freshness_seconds=0,
        )
    except ValueError as exc:
        assert "freshness_seconds" in str(exc)
    else:
        raise AssertionError("Expected freshness validation to fail")


def test_health_observation_rejects_blank_names():
    observed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    try:
        HealthObservation(
            dimension=HealthDimension.PERSISTENCE,
            name=" ",
            status=HealthCheckStatus.PASS,
            observed_at=observed_at,
        )
    except ValueError as exc:
        assert "name" in str(exc)
    else:
        raise AssertionError("Expected name validation to fail")

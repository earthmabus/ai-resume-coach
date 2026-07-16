from __future__ import annotations

from core.runtime_identity import RuntimeIdentity


def identity() -> RuntimeIdentity:
    return RuntimeIdentity(
        project_name="ai-resume-coach",
        environment="test",
        app_version="1.2.3",
        deployment_id="deployment-1234567890",
        region="us-east-1",
    )


def test_runtime_identity_metadata_contract():
    runtime = identity()

    assert runtime.creation_metadata() == {
        "createdRegion": "us-east-1",
        "createdByDeploymentId": "deployment-1234567890",
        "lastUpdatedRegion": "us-east-1",
        "lastUpdatedByDeploymentId": "deployment-1234567890",
    }

    assert runtime.update_metadata() == {
        "lastUpdatedRegion": "us-east-1",
        "lastUpdatedByDeploymentId": "deployment-1234567890",
    }

    assert runtime.processing_metadata() == {
        "processedRegion": "us-east-1",
        "processedByDeploymentId": "deployment-1234567890",
    }


def test_runtime_identity_shortens_deployment_for_display():
    assert identity().short_deployment_id == "deployment-1"

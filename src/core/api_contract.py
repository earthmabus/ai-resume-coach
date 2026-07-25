from __future__ import annotations


PUBLIC_API_ROUTES: tuple[str, ...] = (
    "GET /health",
    "GET /health/live",
    "GET /health/ready",
)

HANDLER_ONLY_ROUTES: tuple[str, ...] = (
    "GET /version",
)

PROTECTED_API_ROUTES: tuple[str, ...] = (
    "DELETE /analysis/{id}",
    "DELETE /analyses",
    "DELETE /job-match/{id}",
    "DELETE /job-matches",
    "GET /analyses",
    "GET /analysis/{id}",
    "GET /analysis/{id}/download-url",
    "GET /job-match/{id}",
    "GET /job-match/{matchId}/interview-prep",
    "GET /job-match/{matchId}/tailoring",
    "GET /job-matches",
    "GET /profile",
    "GET /resume-tailoring/{id}",
    "DELETE /target-careers/{id}",
    "GET /target-careers",
    "GET /target-careers/{id}",
    "GET /target-careers/generations/{id}",
    "POST /analyze-resume",
    "POST /analyze-uploaded-resume",
    "POST /match-job-description",
    "POST /resume-upload-url",
    "POST /tailor-resume",
    "PUT /profile",
    "POST /target-careers",
    "POST /target-careers/generate-details",
    "PUT /target-careers/{id}",
)

LEGACY_OBSOLETE_ROUTES: tuple[str, ...] = (
    "DELETE /job-matching/{matchId}",
    "GET /job-matching",
    "POST /job-matching",
    "POST /resume-analysis",
    "POST /resume-tailoring",
)


def deployed_api_routes() -> tuple[str, ...]:
    return tuple(sorted((*PUBLIC_API_ROUTES, *PROTECTED_API_ROUTES)))


def handler_route_contract() -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                *PUBLIC_API_ROUTES,
                *HANDLER_ONLY_ROUTES,
                *PROTECTED_API_ROUTES,
            )
        )
    )

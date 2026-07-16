import os
from datetime import datetime, timezone

# import core utilities
from core.responses import build_response
from core.routes import route_request
from core.config import get_config
from core.health import live, ready

# import features
from features.profile import get_profile, update_profile
from features.target_career import get_target_career, update_target_career
from features.job_matching import match_job_description, list_job_matches, get_job_match, delete_job_match, delete_all_job_matches
from features.resume_analysis import analyze_resume, analyze_uploaded_resume, create_resume_upload_url, delete_all_analyses, delete_analysis, get_analysis, get_resume_download_url, list_analyses
from features.resume_tailoring import tailor_resume, get_resume_tailoring, get_resume_tailoring_by_match, get_interview_prep_by_match


def health(event=None):
    config = get_config()

    return build_response(
        200,
        {
            "status": "ok",
            "project": config.project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "region": config.aws_region,
            "environment": config.environment,
            "deploymentId": config.deployment_id,
        },
    )


def version(event=None):
    config = get_config()

    return build_response(
        200,
        {
            "application": config.project_name,
            "version": config.app_version,
            "environment": config.environment,
            "analysisProvider": config.analysis_provider,
            "openaiModel": config.openai_model,
            "region": config.aws_region,
            "deploymentId": config.deployment_id,
        },
    )


def lambda_handler(event, context):
    routes = {
        # /health - application status
        # /health/live - lambda process and router alive
        # /health/ready - region can safely accept requests
        # /version - build and runtime metadata
        "GET /health": health,
        "GET /health/live": live,
        "GET /health/ready": ready,
        "GET /version": version,

        # features/resume_analysis.py
        "POST /analyze-resume": analyze_resume,
        "POST /analyze-uploaded-resume": analyze_uploaded_resume,
        "GET /analyses": list_analyses,
        "GET /analysis/{id}": get_analysis,
        "GET /analysis/{id}/download-url": get_resume_download_url,
        "POST /resume-upload-url": create_resume_upload_url,
        "DELETE /analysis/{id}": delete_analysis,
        "DELETE /analyses": delete_all_analyses,

        # features/job_matching.py
        "POST /match-job-description": match_job_description,
        "GET /job-matches": list_job_matches,
        "GET /job-match/{id}": get_job_match,
        "DELETE /job-match/{id}": delete_job_match,
        "DELETE /job-matches": delete_all_job_matches,

        # features/resume_tailoring.py
        "POST /tailor-resume": tailor_resume,
        "GET /resume-tailoring/{id}": get_resume_tailoring,
        "GET /job-match/{matchId}/tailoring": get_resume_tailoring_by_match,
        "GET /job-match/{matchId}/interview-prep": get_interview_prep_by_match,

        # features/profile.py
        "GET /profile": get_profile,
        "PUT /profile": update_profile,

        # features/target_career.py
        "GET /target-career": get_target_career,
        "PUT /target-career": update_target_career,
    }

    return route_request(event, routes)

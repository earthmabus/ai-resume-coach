import os
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

# import core utilities
from core.responses import build_response, parse_body
from core.routes import route_request
from core.auth import current_user_id, assert_item_owner
from core.keys import (
    base_keys,
    resume_sk,
    tailoring_pk,
    tailoring_sk,
    user_pk,
)
from core.storage import document_bucket, get_entity_by_id, resume_analysis_queue_url, s3, sqs, table

# import features
from features.profile import get_profile, update_profile
from features.target_career import get_target_career_for_user, get_target_career, update_target_career
from features.job_matching import match_job_description, list_job_matches, get_job_match, delete_job_match, delete_all_job_matches
from features.resume_analysis import analyze_resume, analyze_uploaded_resume, create_resume_upload_url, delete_all_analyses, delete_analysis, get_analysis, get_resume_download_url, list_analyses

def health():
    return build_response(
        200,
        {
            "status": "ok",
            "project": os.getenv("PROJECT_NAME", "ai-resume-coach"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def version():
    return build_response(
        200,
        {
            "application": os.getenv("PROJECT_NAME", "ai-resume-coach"),
            "version": os.getenv("APP_VERSION", "0.1.0"),
            "environment": os.getenv("ENVIRONMENT", "dev"),
            "analysisProvider": os.getenv("ANALYSIS_PROVIDER", "rule-based"),
            "openaiModel": os.getenv("OPENAI_MODEL", ""),
        },
    )


def tailor_resume(event):
    body = parse_body(event)

    user_id = current_user_id(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    match_id = body.get("matchId", "").strip()
    requested_provider = body.get("analysisProvider")

    if not match_id:
        return build_response(400, {"error": "matchId is required"})

    match_item = get_entity_by_id(match_id, "jobMatch")

    if not match_item:
        return build_response(404, {"error": "job match not found"})

    if match_item.get("recordType") != "jobMatch":
        return build_response(400, {"error": "record is not a job match"})

    if match_item.get("status") != "completed":
        return build_response(400, {"error": "job match must be completed before tailoring"})

    resume_text = match_item.get("resumeText", "").strip()
    job_description_text = match_item.get("jobDescriptionText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "job match does not contain resumeText"})

    if not job_description_text:
        return build_response(400, {"error": "job match does not contain jobDescriptionText"})

    tailoring_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        **base_keys(
            pk=tailoring_pk(match_id),
            sk=tailoring_sk(tailoring_id),
            entity_id=tailoring_id,
            record_type="resumeTailoring",
        ),
        "userId": user_id,
        "analysisId": tailoring_id,
        "tailoringId": tailoring_id,
        "matchId": match_id,
        "resumeAnalysisId": match_item.get("resumeAnalysisId", ""),
        "recordType": "resumeTailoring",
        "createdAt": created_at,
        "status": "processing",
        "provider": requested_provider or match_item.get("provider") or os.getenv("ANALYSIS_PROVIDER", "rule-based"),
        "model": os.getenv("OPENAI_MODEL", ""),
        "analysisVersion": "resume-tailoring-queued-v1",
        "analysisDurationMs": 0,
        "jobName": match_item.get("jobName", "Untitled Job"),
        "jobUrl": match_item.get("jobUrl", ""),
        "resumeName": match_item.get("resumeName", "Untitled Resume"),
        "resumeText": resume_text,
        "jobDescriptionText": job_description_text,
        "resumeDocumentBucket": match_item.get("resumeDocumentBucket", ""),
        "resumeDocumentKey": match_item.get("resumeDocumentKey", ""),
        "resumeFileName": match_item.get("resumeFileName", ""),
        "tailoredExecutiveSummary": "",
        "tailoredResumeBullets": [],
        "keywordsToAdd": [],
        "rolePositioningAdvice": [],
        "atsOptimizationAdvice": [],
        "rewriteWarnings": [],
    }

    table.put_item(Item=item)

    sqs.send_message(
        QueueUrl=resume_analysis_queue_url,
        MessageBody=json.dumps(
            {
                "userId": user_id,
                "jobType": "resumeTailoring",
                "tailoringId": tailoring_id,
                "analysisProvider": requested_provider,
            }
        ),
    )

    return build_response(202, item)


def get_resume_tailoring(event):
    user_id = current_user_id(event)

    tailoring_id = event.get("pathParameters", {}).get("id")

    if not tailoring_id:
        return build_response(400, {"error": "tailoring id is required"})

    item = get_entity_by_id(tailoring_id, "resumeTailoring")

    if not item:
        return build_response(404, {"error": "tailoring not found"})

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    return build_response(200, item)


def get_resume_tailoring_by_match(event):
    user_id = current_user_id(event)
    match_id = event.get("pathParameters", {}).get("matchId")

    if not match_id:
        return build_response(400, {"error": "match id is required"})

    response = table.query(
        KeyConditionExpression=Key("pk").eq(f"MATCH#{match_id}") & Key("sk").begins_with("TAILORING#")
    )

    items = response.get("Items", [])

    if not items:
        return build_response(404, {"error": "tailoring not found for match"})

    items = sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)
    item = items[0]

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    return build_response(200, item)


def get_interview_prep_by_match(event):
    user_id = current_user_id(event)
    match_id = event.get("pathParameters", {}).get("matchId")

    if not match_id:
        return build_response(400, {"error": "match id is required"})

    response = table.query(
        KeyConditionExpression=Key("pk").eq(f"MATCH#{match_id}") & Key("sk").begins_with("INTERVIEW#")
    )

    items = response.get("Items", [])

    if not items:
        return build_response(404, {"error": "interview preparation not found for match"})

    items = sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)
    item = items[0]

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    return build_response(200, item)


def lambda_handler(event, context):
    routes = {
        "GET /health": health,
        "GET /version": version,

        # completed refactoring
        "POST /analyze-resume": analyze_resume,
        "POST /analyze-uploaded-resume": analyze_uploaded_resume,
        "GET /analyses": list_analyses,
        "GET /analysis/{id}": get_analysis,
        "GET /analysis/{id}/download-url": get_resume_download_url,
        "POST /resume-upload-url": create_resume_upload_url,
        "DELETE /analysis/{id}": delete_analysis,
        "DELETE /analyses": delete_all_analyses,

        # completed refactoring
        "POST /match-job-description": match_job_description,
        "GET /job-matches": list_job_matches,
        "GET /job-match/{id}": get_job_match,
        "DELETE /job-match/{id}": delete_job_match,
        "DELETE /job-matches": delete_all_job_matches,

        # resume_tailoring.py
        "POST /tailor-resume": tailor_resume,
        "GET /resume-tailoring/{id}": get_resume_tailoring,
        "GET /job-match/{matchId}/tailoring": get_resume_tailoring_by_match,

        # interview_preparation.py
        "GET /job-match/{matchId}/interview-prep": get_interview_prep_by_match,

        # completed refactoring
        "GET /profile": get_profile,
        "PUT /profile": update_profile,

        # completed refactoring
        "GET /target-career": get_target_career,
        "PUT /target-career": update_target_career,
    }

    return route_request(event, routes)

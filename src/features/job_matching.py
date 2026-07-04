import json
import os
import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

# imports from project specific files
from core.responses import build_response, parse_body
from core.auth import current_user_id, assert_item_owner
from core.keys import (
    base_keys,
    interview_sk,
    match_sk,
    tailoring_pk,
    tailoring_sk,
    user_pk,
)
from core.storage import (
    get_entity_by_id,
    resume_analysis_queue_url,
    sqs,
    table,
)

def match_job_description(event):
    body = parse_body(event)

    user_id = current_user_id(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    analysis_id = body.get("analysisId", "").strip()
    job_name = body.get("jobName", "").strip() or "Untitled Job"
    job_url = body.get("jobUrl", "").strip()
    job_description_text = body.get("jobDescriptionText", "").strip()
    requested_provider = body.get("analysisProvider")

    if not analysis_id:
        return build_response(400, {"error": "analysisId is required"})

    if not job_description_text:
        return build_response(400, {"error": "jobDescriptionText is required"})

    resume_item = get_entity_by_id(analysis_id, "resumeAnalysis")

    if not resume_item:
        return build_response(404, {"error": "resume analysis not found"})

    try:
        assert_item_owner(resume_item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    resume_text = resume_item.get("resumeText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "resume analysis does not contain resumeText"})

    match_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    
    tailoring_id = str(uuid.uuid4())

    interview_prep_id = str(uuid.uuid4())

    item = {
        **base_keys(
            pk=user_pk(user_id),
            sk=match_sk(match_id),
            entity_id=match_id,
            record_type="jobMatch",
        ),
        "recordType": "jobMatch",
        "userId": user_id,
        "analysisId": match_id,
        "matchId": match_id,
        "resumeAnalysisId": analysis_id,
        "tailoringId": tailoring_id,
        "interviewPrepId": interview_prep_id,
        "createdAt": created_at,
        "status": "processing",
        "jobName": job_name,
        "jobUrl": job_url,
        "provider": requested_provider or os.getenv("ANALYSIS_PROVIDER", "rule-based"),
        "model": os.getenv("OPENAI_MODEL", ""),
        "analysisVersion": "job-match-queued-v1",
        "analysisDurationMs": 0,
        "matchScore": 0,
        "leadershipMatchScore": 0,
        "technicalMatchScore": 0,
        "architectureMatchScore": 0,
        "atsKeywordScore": 0,
        "matchedKeywords": [],
        "missingKeywords": [],
        "leadershipGaps": [],
        "technicalGaps": [],
        "recommendedResumeChanges": [
            "Job match has been queued for asynchronous AI analysis."
        ],
        "executiveSummary": "Job match is processing.",
        "jobDescriptionText": job_description_text,
        "resumeName": resume_item.get("resumeName", "Untitled Resume"),
        "resumeSourceType": resume_item.get("sourceType", ""),
        "resumeScore": resume_item.get("score", 0),
        "resumeCreatedAt": resume_item.get("createdAt", ""),
        "resumeFileName": resume_item.get("fileName", ""),
        "resumeDocumentBucket": resume_item.get("documentBucket", ""),
        "resumeDocumentKey": resume_item.get("documentKey", ""),
        "resumeText": resume_text,
    }

    table.put_item(Item=item)

    sqs.send_message(
        QueueUrl=resume_analysis_queue_url,
        MessageBody=json.dumps(
            {
                "userId": user_id,
                "jobType": "jobMatch",
                "matchId": match_id,
                "analysisId": analysis_id,
                "analysisProvider": requested_provider,
            }
        ),
    )

    tailoring_item = {
        **base_keys(
            pk=tailoring_pk(match_id),
            sk=tailoring_sk(tailoring_id),
            entity_id=tailoring_id,
            record_type="resumeTailoring",
        ),
        "recordType": "resumeTailoring",
        "userId": user_id,
        "analysisId": tailoring_id,
        "tailoringId": tailoring_id,
        "matchId": match_id,
        "resumeAnalysisId": analysis_id,
        "createdAt": created_at,
        "status": "waiting",
        "provider": requested_provider or os.getenv("ANALYSIS_PROVIDER", "rule-based"),
        "model": os.getenv("OPENAI_MODEL", ""),
        "analysisVersion": "resume-tailoring-waiting-v1",
        "analysisDurationMs": 0,
        "jobName": job_name,
        "jobUrl": job_url,
        "resumeName": resume_item.get("resumeName", "Untitled Resume"),
        "resumeText": resume_text,
        "jobDescriptionText": job_description_text,
        "resumeDocumentBucket": resume_item.get("documentBucket", ""),
        "resumeDocumentKey": resume_item.get("documentKey", ""),
        "resumeFileName": resume_item.get("fileName", ""),
        "tailoredExecutiveSummary": "",
        "tailoredResumeBullets": [],
        "keywordsToAdd": [],
        "rolePositioningAdvice": [],
        "atsOptimizationAdvice": [],
        "rewriteWarnings": [],
    }

    table.put_item(Item=tailoring_item)

    interview_prep_item = {
        **base_keys(
            pk=tailoring_pk(match_id),
            sk=interview_sk(interview_prep_id),
            entity_id=interview_prep_id,
            record_type="interviewPreparation",
        ),
        "recordType": "interviewPreparation",
        "userId": user_id,
        "analysisId": interview_prep_id,
        "interviewPrepId": interview_prep_id,
        "matchId": match_id,
        "resumeAnalysisId": analysis_id,
        "createdAt": created_at,
        "status": "waiting",
        "provider": requested_provider or os.getenv("ANALYSIS_PROVIDER", "rule-based"),
        "model": os.getenv("OPENAI_MODEL", ""),
        "analysisVersion": "interview-prep-waiting-v1",
        "analysisDurationMs": 0,
        "jobName": job_name,
        "jobUrl": job_url,
        "resumeName": resume_item.get("resumeName", "Untitled Resume"),
        "resumeText": resume_text,
        "jobDescriptionText": job_description_text,
        "behavioralQuestions": [],
        "leadershipQuestions": [],
        "systemDesignQuestions": [],
        "cloudArchitectureQuestions": [],
        "securityQuestions": [],
        "resumeSpecificQuestions": [],
        "jobSpecificQuestions": [],
        "interviewReadinessSummary": "",
    }

    table.put_item(Item=interview_prep_item)

    return build_response(202, item)


def list_job_matches(event):
    user_id = current_user_id(event)

    response = table.query(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id)) & Key("sk").begins_with("MATCH#")
    )

    matches = sorted(
        response.get("Items", []),
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, {"jobMatches": matches})


def get_job_match(event):
    user_id = current_user_id(event)
    match_id = event.get("pathParameters", {}).get("id")

    if not match_id:
        return build_response(400, {"error": "match id is required"})

    item = get_entity_by_id(match_id, "jobMatch")

    if not item:
        return build_response(404, {"error": "job match not found"})

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    return build_response(200, item)


def delete_job_match(event):
    user_id = current_user_id(event)
    match_id = event.get("pathParameters", {}).get("id")

    if not match_id:
        return build_response(400, {"error": "match id is required"})

    item = get_entity_by_id(match_id, "jobMatch")

    if not item:
        return build_response(404, {"error": "job match not found"})

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    deleted = 0

    child_response = table.query(
        KeyConditionExpression=Key("pk").eq(f"MATCH#{match_id}")
    )

    for child in child_response.get("Items", []):
        try:
            assert_item_owner(child, user_id)
        except PermissionError:
            continue

        table.delete_item(Key={"pk": child["pk"], "sk": child["sk"]})
        deleted += 1

    table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
    deleted += 1

    return build_response(200, {
        "deleted": True,
        "deletedCount": deleted,
        "matchId": match_id
    })


def delete_all_job_matches(event):
    user_id = current_user_id(event)

    response = table.query(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id)) & Key("sk").begins_with("MATCH#")
    )

    deleted = 0

    for match in response.get("Items", []):
        match_id = match.get("matchId")

        if match_id:
            child_response = table.query(
                KeyConditionExpression=Key("pk").eq(f"MATCH#{match_id}")
            )

            for child in child_response.get("Items", []):
                try:
                    assert_item_owner(child, user_id)
                except PermissionError:
                    continue

                table.delete_item(Key={"pk": child["pk"], "sk": child["sk"]})
                deleted += 1

        table.delete_item(Key={"pk": match["pk"], "sk": match["sk"]})
        deleted += 1

    return build_response(200, {
        "deleted": deleted,
        "recordType": "jobMatchBundle"
    })

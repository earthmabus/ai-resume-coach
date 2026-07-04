import json
import os
import uuid
import time 
from datetime import datetime, timezone
from io import BytesIO

from boto3.dynamodb.conditions import Key

from pypdf import PdfReader

# imports from project specific files
from providers.factory import get_analysis_provider
from core.responses import build_response, parse_body
from core.routes import route_request
from core.auth import current_user_id, assert_item_owner
from core.keys import (
    base_keys,
    interview_sk,
    match_sk,
    resume_sk,
    tailoring_pk,
    tailoring_sk,
    user_pk,
)
from core.storage import (
    document_bucket,
    get_entity_by_id,
    resume_analysis_queue_url,
    s3,
    sqs,
    table,
)
from core.profile import get_profile, update_profile
from core.target_career import get_target_career_for_user, get_target_career, update_target_career

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

def analyze_and_save_resume(
    user_id,
    resume_text,
    source_type,
    document_bucket_name="",
    document_key="",
    file_name="",
    requested_provider=None,
    resume_name="Untitled Resume",
):
    analysis_started = time.perf_counter()
    resume_text = (resume_text or "").strip()

    if not resume_text:
        return build_response(
            400,
            {
                "error": "No resume text could be analyzed",
                "sourceType": source_type,
            },
        )

    analysis_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    target_career = get_target_career_for_user(user_id)

    if not target_career:
        return build_response(400, {
            "error": "Target Career is required before analyzing resumes"
        })

    provider = get_analysis_provider(requested_provider)
    analysis_result = provider.analyze(resume_text, target_career)

    analysis_duration_ms = int((time.perf_counter() - analysis_started) * 1000)

    item = {
        **base_keys(
            pk=user_pk(user_id),
            sk=resume_sk(analysis_id),
            entity_id=analysis_id,
            record_type="resumeAnalysis",
        ),
        "recordType": "resumeAnalysis",
        "userId": user_id,
        "analysisId": analysis_id,
        "createdAt": created_at,
        "sourceType": source_type,
        "status": "completed",
        "provider": analysis_result["provider"],
        "model": analysis_result.get("model", ""),
        "analysisVersion": analysis_result["analysisVersion"],
        "analysisDurationMs": analysis_duration_ms,
        "score": analysis_result["score"],
        "wordCount": analysis_result["wordCount"],
        "resumeName": resume_name,
        "resumeText": resume_text,
        "strengths": analysis_result["strengths"],
        "recommendations": analysis_result["recommendations"],
        "executiveSummary": analysis_result.get("executiveSummary", ""),
        "documentBucket": document_bucket_name,
        "documentKey": document_key,
        "fileName": file_name,
        "targetCareer": target_career,
        "targetRoleTitle": target_career.get("roleTitle", ""),
        "targetIndustry": target_career.get("industry", ""),
        "dynamicScores": analysis_result.get("dynamicScores", []),
        "roleFitSummary": analysis_result.get("roleFitSummary", ""),
        "roleSpecificGaps": analysis_result.get("roleSpecificGaps", []),
    }

    table.put_item(Item=item)

    return build_response(200, item)


def analyze_resume(event):
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    user_id = current_user_id(event)
    resume_name = body.get("resumeName", "").strip() or "Untitled Resume"
    resume_text = body.get("resumeText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "resumeText is required"})

    requested_provider = body.get("analysisProvider")

    return analyze_and_save_resume(
        user_id=user_id,
        resume_text=resume_text,
        source_type="text",
        requested_provider=requested_provider,
        resume_name=resume_name,
    )


def create_resume_upload_url(event):
    body = parse_body(event)

    user_id = current_user_id(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    file_name = body.get("fileName", "").strip()
    content_type = body.get("contentType", "application/pdf").strip()

    if not file_name:
        return build_response(400, {"error": "fileName is required"})

    if content_type != "application/pdf":
        return build_response(
            400,
            {"error": "Only application/pdf uploads are currently supported"},
        )

    upload_id = str(uuid.uuid4())
    document_key = f"uploads/{upload_id}/{file_name}"

    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": document_bucket,
            "Key": document_key,
            "ContentType": content_type,
        },
        ExpiresIn=900,
    )

    return build_response(
        200,
        {
            "uploadId": upload_id,
            "uploadUrl": upload_url,
            "documentBucket": document_bucket,
            "documentKey": document_key,
            "fileName": file_name,
            "contentType": content_type,
            "expiresInSeconds": 900,
        },
    )


def extract_text_from_pdf(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    pdf_bytes = response["Body"].read()

    reader = PdfReader(BytesIO(pdf_bytes))
    extracted_pages = []

    for page in reader.pages:
        extracted_pages.append(page.extract_text() or "")

    return "\n".join(extracted_pages).strip()


def analyze_uploaded_resume(event):
    body = parse_body(event)

    user_id = current_user_id(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    target_career = get_target_career_for_user(user_id)

    if not target_career:
        return build_response(400, {
            "error": "Target Career is required before analyzing resumes"
        })

    file_name = body.get("fileName", "").strip()
    resume_name = body.get("resumeName", "").strip() or file_name or "Untitled Resume"
    document_key = body.get("documentKey", "").strip()
    bucket_name = body.get("documentBucket", document_bucket).strip()

    if not document_key:
        return build_response(400, {"error": "documentKey is required"})

    try:
        extracted_text = extract_text_from_pdf(bucket_name, document_key)
    except Exception as error:
        return build_response(
            500,
            {
                "error": "Failed to extract text from PDF",
                "details": str(error),
                "documentBucket": bucket_name,
                "documentKey": document_key,
                "fileName": file_name,
            },
        )

    try:
        analysis_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        requested_provider = body.get("analysisProvider", os.getenv("ANALYSIS_PROVIDER", "rule-based"))

        item = {
            **base_keys(
                pk=user_pk(user_id),
                sk=resume_sk(analysis_id),
                entity_id=analysis_id,
                record_type="resumeAnalysis",
            ),
            "recordType": "resumeAnalysis",
            "userId": user_id,
            "analysisId": analysis_id,
            "createdAt": created_at,
            "sourceType": "pdf",
            "status": "processing",
            "provider": os.getenv("ANALYSIS_PROVIDER", "rule-based"),
            "model": os.getenv("OPENAI_MODEL", ""),
            "analysisVersion": "pdf-extraction-v1",
            "analysisDurationMs": 0,
            "score": 0,
            "wordCount": len(extracted_text.split()),
            "resumeName": resume_name,
            "resumeText": extracted_text,
            "strengths": [
                 "PDF uploaded successfully",
                 "Resume text extracted successfully",
                 "Resume is queued for AI analysis"
            ],
            "recommendations": [
                 "AI analysis will be completed asynchronously in a future processing phase."
            ],
            "executiveSummary": "PDF text was extracted and saved. AI analysis is pending.",
            "documentBucket": bucket_name,
            "documentKey": document_key,
            "fileName": file_name,
            "requestedProvider": requested_provider,
            "targetCareer": target_career,
            "targetRoleTitle": target_career.get("roleTitle", ""),
            "targetIndustry": target_career.get("industry", ""),
            "dynamicScores": [],
            "roleFitSummary": "",
            "roleSpecificGaps": [],
        }

        table.put_item(Item=item)

        sqs.send_message(
            QueueUrl=resume_analysis_queue_url,
            MessageBody=json.dumps(
                {
                    "userId": user_id,
                    "analysisId": analysis_id,
                    "sourceType": "pdf",
                    "analysisProvider": requested_provider
                }
            ),
        )

        return build_response(202, item)
    except Exception as error:
        return build_response(
            500,
            {
                "error": "PDF analysis save failed",
                "details": str(error),
                "documentBucket": bucket_name,
                "documentKey": document_key,
                "fileName": file_name,
                "extractedTextLength": len(extracted_text),
            },
        )


def list_analyses(event):
    user_id = current_user_id(event)

    response = table.query(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id)) & Key("sk").begins_with("RESUME#")
    )

    analyses = sorted(
        response.get("Items", []),
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, {"analyses": analyses})


def get_analysis(event):
    analysis_id = event.get("pathParameters", {}).get("id")

    user_id = current_user_id(event)

    if not analysis_id:
        return build_response(400, {"error": "analysis id is required"})

    item = get_entity_by_id(analysis_id, "resumeAnalysis")

    if not item:
        return build_response(404, {"error": "analysis not found"})

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    return build_response(200, item)


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


def delete_s3_document_if_present(item):
    bucket = item.get("documentBucket", "")
    key = item.get("documentKey", "")

    if bucket and key:
        try:
            s3.delete_object(Bucket=bucket, Key=key)
        except Exception:
            pass


def delete_analysis(event):
    user_id = current_user_id(event)
    analysis_id = event.get("pathParameters", {}).get("id")

    if not analysis_id:
        return build_response(400, {"error": "analysis id is required"})

    item = get_entity_by_id(analysis_id, "resumeAnalysis")

    if not item:
        return build_response(404, {"error": "analysis not found"})

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    table.delete_item(
        Key={
            "pk": item["pk"],
            "sk": item["sk"],
        }
    )

    return build_response(200, {"deleted": True, "analysisId": analysis_id})


def delete_all_analyses(event):
    user_id = current_user_id(event)

    response = table.query(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id)) & Key("sk").begins_with("RESUME#")
    )

    deleted = 0

    for item in response.get("Items", []):
        table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
        deleted += 1

    return build_response(200, {"deleted": deleted, "recordType": "resumeAnalysis"})


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


def get_resume_download_url(event):
    user_id = current_user_id(event)

    analysis_id = event.get("pathParameters", {}).get("id")

    if not analysis_id:
        return build_response(400, {"error": "analysis id is required"})

    item = get_entity_by_id(analysis_id, "resumeAnalysis")

    if not item:
        return build_response(404, {"error": "analysis not found"})

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    bucket = item.get("documentBucket", "")
    key = item.get("documentKey", "")

    if not bucket or not key:
        return build_response(400, {"error": "analysis does not have an uploaded document"})

    download_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": bucket,
            "Key": key,
        },
        ExpiresIn=900,
    )

    return build_response(
        200,
        {
            "downloadUrl": download_url,
            "expiresInSeconds": 900,
            "fileName": item.get("fileName", ""),
            "resumeName": item.get("resumeName", ""),
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
        "POST /analyze-resume": analyze_resume,
        "POST /resume-upload-url": create_resume_upload_url,
        "POST /analyze-uploaded-resume": analyze_uploaded_resume,
        "GET /analyses": list_analyses,
        "GET /analysis/{id}": get_analysis,
        "POST /match-job-description": match_job_description,
        "GET /job-matches": list_job_matches,
        "GET /job-match/{id}": get_job_match,
        "DELETE /analysis/{id}": delete_analysis,
        "DELETE /analyses": delete_all_analyses,
        "DELETE /job-match/{id}": delete_job_match,
        "DELETE /job-matches": delete_all_job_matches,
        "GET /analysis/{id}/download-url": get_resume_download_url,
        "POST /tailor-resume": tailor_resume,
        "GET /resume-tailoring/{id}": get_resume_tailoring,
        "GET /job-match/{matchId}/tailoring": get_resume_tailoring_by_match,
        "GET /profile": get_profile,
        "PUT /profile": update_profile,
        "GET /job-match/{matchId}/interview-prep": get_interview_prep_by_match,
        "GET /target-career": get_target_career,
        "PUT /target-career": update_target_career,
    }

    return route_request(event, routes)

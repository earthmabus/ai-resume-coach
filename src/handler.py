import json
import os
import uuid
import time 
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

import boto3
from boto3.dynamodb.conditions import Key, Attr

from pypdf import PdfReader

from providers.factory import get_analysis_provider

sqs = boto3.client("sqs")
resume_analysis_queue_url = os.getenv("RESUME_ANALYSIS_QUEUE_URL")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("RESUME_ANALYSIS_TABLE"))

s3 = boto3.client("s3")
document_bucket = os.getenv("DOCUMENT_BUCKET")


def json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, default=json_default),
    }


def parse_body(event):
    try:
        return json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return None


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
            "dynamicScores": analysis_result.get("dynamicScores", []),
            "roleFitSummary": analysis_result.get("roleFitSummary", ""),
            "roleSpecificGaps": analysis_result.get("roleSpecificGaps", []),
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
        "recordType": "jobMatch",
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
        "recordType": "resumeTailoring",
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
        "recordType": "interviewPreparation",
        "createdAt": created_at,
        "status": "waiting",
        "userId": user_id,
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

    table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})

    return build_response(200, {"deleted": True, "matchId": match_id})


def delete_all_job_matches(event):
    user_id = current_user_id(event)

    response = table.query(
        KeyConditionExpression=Key("pk").eq(user_pk(user_id)) & Key("sk").begins_with("MATCH#")
    )

    deleted = 0

    for item in response.get("Items", []):
        table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
        deleted += 1

    return build_response(200, {"deleted": deleted, "recordType": "jobMatch"})


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


def list_resume_tailorings(event):
    user_id = current_user_id(event)

    response = table.scan(
        FilterExpression="userId = :userId AND recordType = :recordType",
        ExpressionAttributeValues={
            ":userId": user_id,
            ":recordType": "resumeTailoring",
        },
    )

    tailorings = sorted(
        response.get("Items", []),
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, {"tailorings": tailorings})


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


def current_user_id(event):
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )

    user_id = claims.get("sub")

    if not user_id:
        raise ValueError("Unauthorized: missing user identity")

    return user_id


def assert_item_owner(item, user_id):
    if item.get("userId") != user_id:
        raise PermissionError("Forbidden")


def get_profile(event):
    user_id = current_user_id(event)

    response = table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": profile_sk(),
        }
    )

    item = response.get("Item")

    if not item:
        return build_response(
            200,
            {
                "pk": user_pk(user_id),
                "sk": profile_sk(),
                "recordType": "userProfile",
                "userId": user_id,
                "name": "",
                "currentTitle": "",
                "targetTitle": "",
                "yearsExperience": "",
                "certifications": "",
                "preferredProvider": "openai",
                "resumeStyle": "executive",
            },
        )

    return build_response(200, item)


def update_profile(event):
    user_id = current_user_id(event)
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    profile_id = f"PROFILE#{user_id}"
    updated_at = datetime.now(timezone.utc).isoformat()

    item = {
        "pk": user_pk(user_id),
        "sk": profile_sk(),
        "recordType": "userProfile",
        "userId": user_id,
        "updatedAt": updated_at,
        "name": body.get("name", "").strip(),
        "currentTitle": body.get("currentTitle", "").strip(),
        "targetTitle": body.get("targetTitle", "").strip(),
        "yearsExperience": body.get("yearsExperience", "").strip(),
        "certifications": body.get("certifications", "").strip(),
        "preferredProvider": body.get("preferredProvider", "openai").strip(),
        "resumeStyle": body.get("resumeStyle", "executive").strip(),
    }

    table.put_item(Item=item)

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


def user_pk(user_id):
    return f"USER#{user_id}"


def resume_sk(analysis_id):
    return f"RESUME#{analysis_id}"


def match_sk(match_id):
    return f"MATCH#{match_id}"


def tailoring_pk(match_id):
    return f"MATCH#{match_id}"


def tailoring_sk(tailoring_id):
    return f"TAILORING#{tailoring_id}"


def interview_sk(interview_prep_id):
    return f"INTERVIEW#{interview_prep_id}"


def profile_sk():
    return "PROFILE"


def entity_gsi_pk(entity_id):
    return f"ENTITY#{entity_id}"


def base_keys(pk, sk, entity_id, record_type):
    return {
        "pk": pk,
        "sk": sk,
        "gsi1pk": entity_gsi_pk(entity_id),
        "gsi1sk": record_type,
    }


def get_entity_by_id(entity_id, expected_record_type=None):
    response = table.query(
        IndexName="gsi1",
        KeyConditionExpression=Key("gsi1pk").eq(entity_gsi_pk(entity_id)),
    )

    items = response.get("Items", [])

    if expected_record_type:
        items = [
            item for item in items
            if item.get("recordType") == expected_record_type
        ]

    return items[0] if items else None


def target_career_sk():
    return "TARGET_CAREER"


def get_target_career_for_user(user_id):
    response = table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": target_career_sk(),
        }
    )
    return response.get("Item")


def get_target_career(event):
    user_id = current_user_id(event)
    item = get_target_career_for_user(user_id)

    if not item:
        return build_response(200, {
            "recordType": "targetCareer",
            "userId": user_id,
            "roleTitle": "",
            "industry": "",
            "seniorityLevel": "",
            "workEnvironment": "",
            "keyResponsibilities": "",
            "requiredSkills": "",
            "certifications": "",
            "physicalRequirements": "",
            "technicalRequirements": "",
            "leadershipRequirements": "",
            "careerGoalSummary": "",
        })

    return build_response(200, item)


def update_target_career(event):
    user_id = current_user_id(event)
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    role_title = body.get("roleTitle", "").strip()
    industry = body.get("industry", "").strip()

    if not role_title or not industry:
        return build_response(400, {"error": "roleTitle and industry are required"})

    target_career_id = f"target-career-{user_id}"
    updated_at = datetime.now(timezone.utc).isoformat()

    item = {
        **base_keys(
            pk=user_pk(user_id),
            sk=target_career_sk(),
            entity_id=target_career_id,
            record_type="targetCareer",
        ),
        "recordType": "targetCareer",
        "targetCareerId": target_career_id,
        "userId": user_id,
        "updatedAt": updated_at,
        "roleTitle": role_title,
        "industry": industry,
        "seniorityLevel": body.get("seniorityLevel", "").strip(),
        "workEnvironment": body.get("workEnvironment", "").strip(),
        "keyResponsibilities": body.get("keyResponsibilities", "").strip(),
        "requiredSkills": body.get("requiredSkills", "").strip(),
        "certifications": body.get("certifications", "").strip(),
        "physicalRequirements": body.get("physicalRequirements", "").strip(),
        "technicalRequirements": body.get("technicalRequirements", "").strip(),
        "leadershipRequirements": body.get("leadershipRequirements", "").strip(),
        "careerGoalSummary": body.get("careerGoalSummary", "").strip(),
    }

    table.put_item(Item=item)
    return build_response(200, item)


def lambda_handler(event, context):
    route = event.get("routeKey")

    if route == "GET /health":
        return health()

    if route == "GET /version":
        return version()

    if route == "POST /analyze-resume":
        return analyze_resume(event)

    if route == "POST /resume-upload-url":
        return create_resume_upload_url(event)

    if route == "POST /analyze-uploaded-resume":
        return analyze_uploaded_resume(event)

    if route == "GET /analyses":
        return list_analyses(event)

    if route == "GET /analysis/{id}":
        return get_analysis(event)

    if route == "POST /match-job-description":
        return match_job_description(event)

    if route == "GET /job-matches":
        return list_job_matches(event)

    if route == "GET /job-match/{id}":
        return get_job_match(event)

    if route == "DELETE /analysis/{id}":
        return delete_analysis(event)

    if route == "DELETE /analyses":
        return delete_all_analyses(event)

    if route == "DELETE /job-match/{id}":
        return delete_job_match(event)

    if route == "DELETE /job-matches":
        return delete_all_job_matches(event)

    if route == "GET /analysis/{id}/download-url":
        return get_resume_download_url(event)

    if route == "POST /tailor-resume":
        return tailor_resume(event)

    if route == "GET /resume-tailorings":
        return list_resume_tailorings(event)

    if route == "GET /resume-tailoring/{id}":
        return get_resume_tailoring(event)

    if route == "GET /job-match/{matchId}/tailoring":
        return get_resume_tailoring_by_match(event)

    if route == "GET /profile":
        return get_profile(event)

    if route == "PUT /profile":
        return update_profile(event)

    if route == "GET /job-match/{matchId}/interview-prep":
        return get_interview_prep_by_match(event)

    if route == "GET /target-career":
        return get_target_career(event)

    if route == "PUT /target-career":
        return update_target_career(event)

    return build_response(404, {"error": "Route not found", "route": route})

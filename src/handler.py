import json
import os
import uuid
import time 
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

import boto3
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
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
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
    resume_text,
    source_type,
    document_bucket_name="",
    document_key="",
    file_name="",
    requested_provider=None,
    resume_name="Untitled Resume",
):
    provider = get_analysis_provider(requested_provider)

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

    provider = get_analysis_provider()
    analysis_result = provider.analyze(resume_text)

    analysis_duration_ms = int((time.perf_counter() - analysis_started) * 1000)

    item = {
        "analysisId": analysis_id,
        "createdAt": created_at,
        "sourceType": source_type,
        "status": "completed",
        "provider": analysis_result["provider"],
        "model": analysis_result.get("model", ""),
        "analysisVersion": analysis_result["analysisVersion"],
        "analysisDurationMs": analysis_duration_ms,
        "score": analysis_result["score"],
        "leadershipScore": analysis_result.get("leadershipScore", 0),
        "technicalScore": analysis_result.get("technicalScore", 0),
        "architectureScore": analysis_result.get("architectureScore", 0),
        "atsScore": analysis_result.get("atsScore", 0),
        "wordCount": analysis_result["wordCount"],
        "resumeName": resume_name,
        "resumeText": resume_text,
        "strengths": analysis_result["strengths"],
        "recommendations": analysis_result["recommendations"],
        "leadershipGaps": analysis_result.get("leadershipGaps", []),
        "technicalGaps": analysis_result.get("technicalGaps", []),
        "executiveSummary": analysis_result.get("executiveSummary", ""),
        "documentBucket": document_bucket_name,
        "documentKey": document_key,
        "fileName": file_name,
    }

    table.put_item(Item=item)

    return build_response(200, item)


def analyze_resume(event):
    body = parse_body(event)

    resume_name = body.get("resumeName", "").strip() or "Untitled Resume"

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    resume_text = body.get("resumeText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "resumeText is required"})

    requested_provider = body.get("analysisProvider")

    return analyze_and_save_resume(
        resume_text=resume_text,
        source_type="text",
        requested_provider=requested_provider,
        resume_name=resume_name,
    )


def create_resume_upload_url(event):
    body = parse_body(event)

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

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    resume_name = body.get("resumeName", "").strip() or file_name or "Untitled Resume"
    document_key = body.get("documentKey", "").strip()
    file_name = body.get("fileName", "").strip()
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
            "analysisId": analysis_id,
            "createdAt": created_at,
            "sourceType": "pdf",
            "status": "processing",
            "provider": os.getenv("ANALYSIS_PROVIDER", "rule-based"),
            "model": os.getenv("OPENAI_MODEL", ""),
            "analysisVersion": "pdf-extraction-v1",
            "analysisDurationMs": 0,
            "score": 0,
            "leadershipScore": 0,
            "technicalScore": 0,
            "architectureScore": 0,
            "atsScore": 0,
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
            "leadershipGaps": [],
            "technicalGaps": [],
            "executiveSummary": "PDF text was extracted and saved. AI analysis is pending.",
            "documentBucket": bucket_name,
            "documentKey": document_key,
            "fileName": file_name,
            "requestedProvider": requested_provider,
        }

        table.put_item(Item=item)

        sqs.send_message(
            QueueUrl=resume_analysis_queue_url,
            MessageBody=json.dumps(
                {
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

def list_analyses():
    response = table.scan(
        ProjectionExpression="analysisId, createdAt, sourceType, #s, score, leadershipScore, technicalScore, architectureScore, atsScore, wordCount, fileName, resumeName, documentBucket, documentKey, provider, model, analysisVersion, analysisDurationMs",
        ExpressionAttributeNames={"#s": "status"},
    )

    analyses = sorted(
        response.get("Items", []),
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, {"analyses": analyses})


def get_analysis(event):
    analysis_id = event.get("pathParameters", {}).get("id")

    if not analysis_id:
        return build_response(400, {"error": "analysis id is required"})

    response = table.get_item(Key={"analysisId": analysis_id})
    item = response.get("Item")

    if not item:
        return build_response(404, {"error": "analysis not found"})

    return build_response(200, item)


def match_job_description(event):
    body = parse_body(event)

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

    resume_response = table.get_item(Key={"analysisId": analysis_id})
    resume_item = resume_response.get("Item")

    if not resume_item:
        return build_response(404, {"error": "resume analysis not found"})

    resume_text = resume_item.get("resumeText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "resume analysis does not contain resumeText"})

    match_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "analysisId": match_id,
        "matchId": match_id,
        "resumeAnalysisId": analysis_id,
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
                "jobType": "jobMatch",
                "matchId": match_id,
                "analysisId": analysis_id,
                "analysisProvider": requested_provider,
            }
        ),
    )

    return build_response(202, item)


def list_job_matches():
    response = table.scan(
        FilterExpression="recordType = :recordType",
        ExpressionAttributeValues={
            ":recordType": "jobMatch"
        },
    )

    matches = sorted(
        response.get("Items", []),
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, {"jobMatches": matches})


def get_job_match(event):
    match_id = event.get("pathParameters", {}).get("id")

    if not match_id:
        return build_response(400, {"error": "job match id is required"})

    response = table.get_item(Key={"analysisId": match_id})
    item = response.get("Item")

    if not item:
        return build_response(404, {"error": "job match not found"})

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
    analysis_id = event.get("pathParameters", {}).get("id")

    if not analysis_id:
        return build_response(400, {"error": "analysis id is required"})

    response = table.get_item(Key={"analysisId": analysis_id})
    item = response.get("Item")

    if not item:
        return build_response(404, {"error": "analysis not found"})

    if item.get("recordType") == "jobMatch":
        return build_response(400, {"error": "use /job-match/{id} to delete job matches"})

    delete_s3_document_if_present(item)

    table.delete_item(Key={"analysisId": analysis_id})

    return build_response(
        200,
        {
            "deleted": True,
            "analysisId": analysis_id,
        },
    )


def delete_all_analyses():
    response = table.scan()
    deleted = 0

    for item in response.get("Items", []):
        if item.get("recordType") == "jobMatch":
            continue

        delete_s3_document_if_present(item)
        table.delete_item(Key={"analysisId": item["analysisId"]})
        deleted += 1

    return build_response(
        200,
        {
            "deleted": deleted,
            "recordType": "resumeAnalysis",
        },
    )


def delete_job_match(event):
    match_id = event.get("pathParameters", {}).get("id")

    if not match_id:
        return build_response(400, {"error": "job match id is required"})

    response = table.get_item(Key={"analysisId": match_id})
    item = response.get("Item")

    if not item:
        return build_response(404, {"error": "job match not found"})

    if item.get("recordType") != "jobMatch":
        return build_response(400, {"error": "record is not a job match"})

    table.delete_item(Key={"analysisId": match_id})

    return build_response(
        200,
        {
            "deleted": True,
            "matchId": match_id,
        },
    )


def delete_all_job_matches():
    response = table.scan(
        FilterExpression="recordType = :recordType",
        ExpressionAttributeValues={
            ":recordType": "jobMatch"
        },
    )

    deleted = 0

    for item in response.get("Items", []):
        table.delete_item(Key={"analysisId": item["analysisId"]})
        deleted += 1

    return build_response(
        200,
        {
            "deleted": deleted,
            "recordType": "jobMatch",
        },
    )


def get_resume_download_url(event):
    analysis_id = event.get("pathParameters", {}).get("id")

    if not analysis_id:
        return build_response(400, {"error": "analysis id is required"})

    response = table.get_item(Key={"analysisId": analysis_id})
    item = response.get("Item")

    if not item:
        return build_response(404, {"error": "analysis not found"})

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
        return list_analyses()

    if route == "GET /analysis/{id}":
        return get_analysis(event)

    if route == "POST /match-job-description":
        return match_job_description(event)

    if route == "GET /job-matches":
        return list_job_matches()

    if route == "GET /job-match/{id}":
        return get_job_match(event)

    if route == "DELETE /analysis/{id}":
        return delete_analysis(event)

    if route == "DELETE /analyses":
        return delete_all_analyses()

    if route == "DELETE /job-match/{id}":
        return delete_job_match(event)

    if route == "DELETE /job-matches":
        return delete_all_job_matches()

    if route == "GET /analysis/{id}/download-url":
        return get_resume_download_url(event)

    return build_response(404, {"error": "Route not found", "route": route})

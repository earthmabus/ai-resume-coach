import json
import os
import uuid
import time 
from datetime import datetime, timezone
from io import BytesIO

from pypdf import PdfReader

from boto3.dynamodb.conditions import Key

# imports from project specific files
from providers.factory import get_analysis_provider
from core.responses import build_response, parse_body
from core.auth import current_user_id, assert_item_owner
from core.keys import base_keys, resume_sk, user_pk
from core.storage import (
    document_bucket,
    get_entity_by_id,
    resume_analysis_queue_url,
    s3,
    sqs,
    table,
)
from features.target_career import get_target_career_for_user


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

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

import boto3
from pypdf import PdfReader


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
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
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
        },
    )


def build_rule_based_analysis(resume_text):
    word_count = len(resume_text.split())

    strengths = [
        "Clear technical leadership foundation",
        "Relevant cloud and engineering management experience",
        "Strong fit for architecture-focused leadership roles",
    ]

    recommendations = [
        "Add measurable business outcomes using numbers, percentages, or dollar impact.",
        "Highlight leadership scope, including team size, delivery ownership, and stakeholder influence.",
        "Strengthen cloud architecture examples by naming AWS services, tradeoffs, and results.",
    ]

    score = min(95, max(60, 70 + min(word_count // 25, 20)))

    return score, word_count, strengths, recommendations


def analyze_and_save_resume(
    resume_text,
    source_type,
    document_bucket_name="",
    document_key="",
    file_name="",
):
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

    score, word_count, strengths, recommendations = build_rule_based_analysis(resume_text)

    item = {
        "analysisId": analysis_id,
        "createdAt": created_at,
        "sourceType": source_type,
        "status": "completed",
        "analysisVersion": "rule-based-v1",
        "score": score,
        "wordCount": word_count,
        "originalText": resume_text,
        "strengths": strengths,
        "recommendations": recommendations,
        "documentBucket": document_bucket_name,
        "documentKey": document_key,
        "fileName": file_name,
    }

    table.put_item(Item=item)

    return build_response(200, item)


def analyze_resume(event):
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    resume_text = body.get("resumeText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "resumeText is required"})

    return analyze_and_save_resume(
        resume_text=resume_text,
        source_type="text",
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

    return analyze_and_save_resume(
        resume_text=extracted_text,
        source_type="pdf",
        document_bucket_name=bucket_name,
        document_key=document_key,
        file_name=file_name,
    )


def list_analyses():
    response = table.scan(
        ProjectionExpression="analysisId, createdAt, sourceType, #s, score, wordCount, fileName",
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

    return build_response(404, {"error": "Route not found", "route": route})

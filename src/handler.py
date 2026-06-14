import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("RESUME_ANALYSIS_TABLE"))


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
    return build_response(200, {
        "status": "ok",
        "project": os.getenv("PROJECT_NAME", "ai-resume-coach"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def version():
    return build_response(200, {
        "application": os.getenv("PROJECT_NAME", "ai-resume-coach"),
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "environment": os.getenv("ENVIRONMENT", "dev"),
    })


def analyze_resume(event):
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    resume_text = body.get("resumeText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "resumeText is required"})

    analysis_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
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

    item = {
        "analysisId": analysis_id,
        "createdAt": created_at,
        "sourceType": body.get("sourceType", "text"),
        "status": "completed",
        "analysisVersion": "rule-based-v1",
        "score": score,
        "wordCount": word_count,
        "originalText": resume_text,
        "strengths": strengths,
        "recommendations": recommendations,
        "documentBucket": body.get("documentBucket", ""),
        "documentKey": body.get("documentKey", ""),
        "fileName": body.get("fileName", ""),
    }

    table.put_item(Item=item)

    return build_response(200, {
        "analysisId": analysis_id,
        "createdAt": created_at,
        "overallScore": score,
        "wordCount": word_count,
        "sourceType": item["sourceType"],
        "status": item["status"],
        "analysisVersion": item["analysisVersion"],
        "strengths": strengths,
        "recommendations": recommendations,
    })


def list_analyses():
    response = table.scan(
        ProjectionExpression="analysisId, createdAt, sourceType, #s, score, wordCount, fileName",
        ExpressionAttributeNames={
            "#s": "status"
        }
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

    if route == "GET /analyses":
        return list_analyses()

    if route == "GET /analysis/{id}":
        return get_analysis(event)

    return build_response(404, {"error": "Route not found", "route": route})

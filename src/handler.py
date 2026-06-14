import json
import os
from datetime import datetime, timezone


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body),
    }


def parse_body(event):
    raw_body = event.get("body") or "{}"

    try:
        return json.loads(raw_body)
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


def analyze_resume(event):
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    resume_text = body.get("resumeText", "").strip()

    if not resume_text:
        return build_response(400, {"error": "resumeText is required"})

    word_count = len(resume_text.split())

    recommendations = [
        "Add measurable business outcomes using numbers, percentages, or dollar impact.",
        "Highlight leadership scope, including team size, delivery ownership, and stakeholder influence.",
        "Strengthen cloud architecture examples by naming AWS services, tradeoffs, and results.",
    ]

    strengths = [
        "Clear technical leadership foundation",
        "Relevant cloud and engineering management experience",
        "Strong fit for architecture-focused leadership roles",
    ]

    score = min(95, max(60, 70 + min(word_count // 25, 20)))

    return build_response(
        200,
        {
            "overallScore": score,
            "wordCount": word_count,
            "strengths": strengths,
            "recommendations": recommendations,
            "analysisType": "placeholder-rule-based",
            "nextStep": "Replace this rule-based logic with Bedrock or OpenAI integration.",
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

    return build_response(404, {"error": "Route not found", "route": route})

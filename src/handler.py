import json
import os
from datetime import datetime, timezone


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }


def health():
    return build_response(
        200,
        {
            "status": "ok",
            "project": os.getenv("PROJECT_NAME"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


def version():
    return build_response(
        200,
        {
            "application": os.getenv("PROJECT_NAME"),
            "version": os.getenv("APP_VERSION", "0.1.0"),
            "environment": os.getenv("ENVIRONMENT")
        }
    )


def analyze_resume(event):
    body = json.loads(event.get("body", "{}"))

    resume_text = body.get("resumeText", "")

    return build_response(
        200,
        {
            "overallScore": 85,
            "resumeLength": len(resume_text),
            "strengths": [
                "Leadership experience",
                "Cloud certifications",
                "Engineering management background"
            ],
            "recommendations": [
                "Add more measurable business outcomes",
                "Quantify team impact",
                "Highlight AI project work"
            ]
        }
    )


def lambda_handler(event, context):

    route = event.get("routeKey")

    if route == "GET /health":
        return health()

    if route == "GET /version":
        return version()

    if route == "POST /analyze-resume":
        return analyze_resume(event)

    return build_response(
        404,
        {
            "error": "Route not found"
        }
    )

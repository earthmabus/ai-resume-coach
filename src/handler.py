import json
import os
from datetime import datetime, timezone


def lambda_handler(event, context):
    response_body = {
        "message": "AI Resume Coach API is running",
        "project": os.getenv("PROJECT_NAME", "ai-resume-coach"),
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(response_body),
    }

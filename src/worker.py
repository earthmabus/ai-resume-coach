import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from providers.factory import get_analysis_provider


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("RESUME_ANALYSIS_TABLE"))


def to_dynamodb_value(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_dynamodb_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_dynamodb_value(v) for v in value]
    return value


def update_analysis_failed(analysis_id, error_message):
    table.update_item(
        Key={"analysisId": analysis_id},
        UpdateExpression="""
            SET #s = :status,
                errorMessage = :errorMessage,
                completedAt = :completedAt
        """,
        ExpressionAttributeNames={
            "#s": "status",
        },
        ExpressionAttributeValues={
            ":status": "failed",
            ":errorMessage": error_message[:1000],
            ":completedAt": datetime.now(timezone.utc).isoformat(),
        },
    )


def process_analysis(analysis_id):
    response = table.get_item(Key={"analysisId": analysis_id})
    item = response.get("Item")

    if not item:
        raise ValueError(f"Analysis not found: {analysis_id}")

    resume_text = item.get("resumeText", "").strip()

    if not resume_text:
        raise ValueError(f"No resumeText found for analysis: {analysis_id}")

    started = time.perf_counter()

    provider = get_analysis_provider()
    analysis_result = provider.analyze(resume_text)

    duration_ms = int((time.perf_counter() - started) * 1000)

    table.update_item(
        Key={"analysisId": analysis_id},
        UpdateExpression="""
            SET #s = :status,
                provider = :provider,
                model = :model,
                analysisVersion = :analysisVersion,
                analysisDurationMs = :analysisDurationMs,
                score = :score,
                leadershipScore = :leadershipScore,
                technicalScore = :technicalScore,
                architectureScore = :architectureScore,
                atsScore = :atsScore,
                wordCount = :wordCount,
                strengths = :strengths,
                recommendations = :recommendations,
                leadershipGaps = :leadershipGaps,
                technicalGaps = :technicalGaps,
                executiveSummary = :executiveSummary,
                completedAt = :completedAt
        """,
        ExpressionAttributeNames={
            "#s": "status",
        },
        ExpressionAttributeValues=to_dynamodb_value(
            {
                ":status": "completed",
                ":provider": analysis_result["provider"],
                ":model": analysis_result.get("model", ""),
                ":analysisVersion": analysis_result["analysisVersion"],
                ":analysisDurationMs": duration_ms,
                ":score": analysis_result["score"],
                ":leadershipScore": analysis_result.get("leadershipScore", 0),
                ":technicalScore": analysis_result.get("technicalScore", 0),
                ":architectureScore": analysis_result.get("architectureScore", 0),
                ":atsScore": analysis_result.get("atsScore", 0),
                ":wordCount": analysis_result["wordCount"],
                ":strengths": analysis_result["strengths"],
                ":recommendations": analysis_result["recommendations"],
                ":leadershipGaps": analysis_result.get("leadershipGaps", []),
                ":technicalGaps": analysis_result.get("technicalGaps", []),
                ":executiveSummary": analysis_result.get("executiveSummary", ""),
                ":completedAt": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )


def lambda_handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        analysis_id = body["analysisId"]

        try:
            process_analysis(analysis_id)
        except Exception as error:
            update_analysis_failed(analysis_id, str(error))
            raise

    return {"status": "ok"}

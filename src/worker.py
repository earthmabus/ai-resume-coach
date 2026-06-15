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


def update_record_failed(record_id, error_message):
    table.update_item(
        Key={"analysisId": record_id},
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


def process_resume_analysis(analysis_id):
    response = table.get_item(Key={"analysisId": analysis_id})
    item = response.get("Item")

    if not item:
        raise ValueError(f"Analysis not found: {analysis_id}")

    resume_text = item.get("resumeText", "").strip()

    if not resume_text:
        raise ValueError(f"No resumeText found for analysis: {analysis_id}")

    requested_provider = item.get("requestedProvider") or item.get("provider")

    started = time.perf_counter()

    provider = get_analysis_provider(requested_provider)
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


def process_job_match(match_id):
    match_response = table.get_item(Key={"analysisId": match_id})
    match_item = match_response.get("Item")

    if not match_item:
        raise ValueError(f"Job match not found: {match_id}")

    resume_analysis_id = match_item.get("resumeAnalysisId")
    job_description_text = match_item.get("jobDescriptionText", "").strip()

    if not resume_analysis_id:
        raise ValueError(f"No resumeAnalysisId found for job match: {match_id}")

    if not job_description_text:
        raise ValueError(f"No jobDescriptionText found for job match: {match_id}")

    resume_response = table.get_item(Key={"analysisId": resume_analysis_id})
    resume_item = resume_response.get("Item")

    if not resume_item:
        raise ValueError(f"Resume analysis not found: {resume_analysis_id}")

    resume_text = resume_item.get("resumeText", "").strip()

    if not resume_text:
        raise ValueError(f"No resumeText found for resume analysis: {resume_analysis_id}")

    requested_provider = match_item.get("provider") or os.getenv("ANALYSIS_PROVIDER", "rule-based")

    started = time.perf_counter()

    provider = get_analysis_provider(requested_provider)
    match_result = provider.match_job_description(resume_text, job_description_text)

    duration_ms = int((time.perf_counter() - started) * 1000)

    table.update_item(
        Key={"analysisId": match_id},
        UpdateExpression="""
            SET #s = :status,
                provider = :provider,
                model = :model,
                analysisVersion = :analysisVersion,
                analysisDurationMs = :analysisDurationMs,
                matchScore = :matchScore,
                leadershipMatchScore = :leadershipMatchScore,
                technicalMatchScore = :technicalMatchScore,
                architectureMatchScore = :architectureMatchScore,
                atsKeywordScore = :atsKeywordScore,
                matchedKeywords = :matchedKeywords,
                missingKeywords = :missingKeywords,
                leadershipGaps = :leadershipGaps,
                technicalGaps = :technicalGaps,
                recommendedResumeChanges = :recommendedResumeChanges,
                executiveSummary = :executiveSummary,
                completedAt = :completedAt
        """,
        ExpressionAttributeNames={
            "#s": "status",
        },
        ExpressionAttributeValues=to_dynamodb_value(
            {
                ":status": "completed",
                ":provider": match_result["provider"],
                ":model": match_result.get("model", ""),
                ":analysisVersion": match_result["analysisVersion"],
                ":analysisDurationMs": duration_ms,
                ":matchScore": match_result["matchScore"],
                ":leadershipMatchScore": match_result.get("leadershipMatchScore", 0),
                ":technicalMatchScore": match_result.get("technicalMatchScore", 0),
                ":architectureMatchScore": match_result.get("architectureMatchScore", 0),
                ":atsKeywordScore": match_result.get("atsKeywordScore", 0),
                ":matchedKeywords": match_result.get("matchedKeywords", []),
                ":missingKeywords": match_result.get("missingKeywords", []),
                ":leadershipGaps": match_result.get("leadershipGaps", []),
                ":technicalGaps": match_result.get("technicalGaps", []),
                ":recommendedResumeChanges": match_result.get("recommendedResumeChanges", []),
                ":executiveSummary": match_result.get("executiveSummary", ""),
                ":completedAt": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )


def lambda_handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record["body"])

        job_type = body.get("jobType", "resumeAnalysis")

        try:
            if job_type == "jobMatch":
                process_job_match(body["matchId"])
            else:
                process_resume_analysis(body["analysisId"])
        except Exception as error:
            record_id = body.get("matchId") or body.get("analysisId")
            update_record_failed(record_id, str(error))
            raise

    return {"status": "ok"}


import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from providers.factory import get_analysis_provider

import logging

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("RESUME_ANALYSIS_TABLE"))
sqs = boto3.client("sqs")
queue_url = os.getenv("RESUME_ANALYSIS_QUEUE_URL")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def to_dynamodb_value(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_dynamodb_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_dynamodb_value(v) for v in value]
    return value


def update_record_failed(record_id, error_message, expected_record_type=None):
    item = get_entity_by_id(record_id, expected_record_type)

    if not item:
        logger.warning("Could not mark record failed because it was not found: %s", record_id)
        return

    table.update_item(
        Key={"pk": item["pk"], "sk": item["sk"]},
        UpdateExpression="""
            SET #s = :status,
                errorMessage = :errorMessage,
                completedAt = :completedAt
        """,
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "failed",
            ":errorMessage": error_message,
            ":completedAt": datetime.now(timezone.utc).isoformat(),
        },
    )


def process_resume_analysis(analysis_id):
    item = get_entity_by_id(analysis_id, "resumeAnalysis")

    if not item:
        raise ValueError(f"Analysis not found: {analysis_id}")

    resume_text = item.get("resumeText", "").strip()

    if not resume_text:
        raise ValueError(f"No resumeText found for analysis: {analysis_id}")

    requested_provider = item.get("requestedProvider") or item.get("provider")

    started = time.perf_counter()

    provider = get_analysis_provider(requested_provider)

    target_career = item.get("targetCareer")

    if not target_career:
        raise ValueError(f"Target career not found for analysis: {analysis_id}")

    analysis_result = provider.analyze(resume_text, target_career)

    duration_ms = int((time.perf_counter() - started) * 1000)

    table.update_item(
        Key={"pk": item["pk"], "sk": item["sk"]},
        UpdateExpression="""
            SET #s = :status,
                provider = :provider,
                model = :model,
                analysisVersion = :analysisVersion,
                analysisDurationMs = :analysisDurationMs,
                score = :score,
                wordCount = :wordCount,
                strengths = :strengths,
                recommendations = :recommendations,
                executiveSummary = :executiveSummary,
                completedAt = :completedAt,
                dynamicScores = :dynamicScores,
                roleFitSummary = :roleFitSummary,
                roleSpecificGaps = :roleSpecificGaps,
                targetRoleTitle = :targetRoleTitle,
                targetIndustry = :targetIndustry,
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
                ":wordCount": analysis_result["wordCount"],
                ":strengths": analysis_result["strengths"],
                ":recommendations": analysis_result["recommendations"],
                ":executiveSummary": analysis_result.get("executiveSummary", ""),
                ":completedAt": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )


def process_job_match(match_id):
    logger.info("Starting job match: %s", str(match_id))
    match_item = get_entity_by_id(match_id, "jobMatch")

    if not match_item:
        logger.info("Raised ValueError since job match not found: %s", str(match_id))
        raise ValueError(f"Job match not found: {match_id}")

    resume_analysis_id = match_item.get("resumeAnalysisId")
    job_description_text = match_item.get("jobDescriptionText", "").strip()

    if not resume_analysis_id:
        logger.info("Raised ValueError since resumeAnalysisId not found for job match: %s", str(match_id))
        raise ValueError(f"No resumeAnalysisId found for job match: {match_id}")

    if not job_description_text:
        logger.info("Raised ValueError since jobDescriptionText not found for job match: %s", str(match_id))
        raise ValueError(f"No jobDescriptionText found for job match: {match_id}")

    resume_item = get_entity_by_id(resume_analysis_id, "resumeAnalysis")

    if not resume_item:
        logger.info("Raised ValueError resume analysis not found for resume analysis: %s", str(resume_analysis_id))
        raise ValueError(f"Resume analysis not found: {resume_analysis_id}")

    resume_text = resume_item.get("resumeText", "").strip()

    if not resume_text:
        logger.info("Raised ValueError since resumeText not found for resume analysis: %s", str(resume_analysis_id))
        raise ValueError(f"No resumeText found for resume analysis: {resume_analysis_id}")

    requested_provider = match_item.get("provider") or os.getenv("ANALYSIS_PROVIDER", "rule-based")

    started = time.perf_counter()

    provider = get_analysis_provider(requested_provider)
    match_result = provider.match_job_description(resume_text, job_description_text)

    duration_ms = int((time.perf_counter() - started) * 1000)

    table.update_item(
        Key={"pk": item["pk"], "sk": item["sk"]},
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

    updated_match_item = get_entity_by_id(match_id, "jobMatch")

    tailoring_id = updated_match_item.get("tailoringId")

    if tailoring_id:
        table.update_item(
            Key={"pk": item["pk"], "sk": item["sk"]},
            UpdateExpression="""
                SET #s = :status,
                analysisVersion = :analysisVersion
            """,
            ExpressionAttributeNames={
                "#s": "status",
            },
            ExpressionAttributeValues={
                ":status": "processing",
                ":analysisVersion": "resume-tailoring-queued-v1",
            },
        )

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                "jobType": "resumeTailoring",
                "tailoringId": tailoring_id
            })
        )

        updated_match_item = get_entity_by_id(match_id, "jobMatch")

        interview_prep_id = updated_match_item.get("interviewPrepId")

        if interview_prep_id:
            table.update_item(
                Key={"pk": item["pk"], "sk": item["sk"]},
                UpdateExpression="""
                    SET #s = :status,
                        analysisVersion = :analysisVersion
                """,
                ExpressionAttributeNames={
                    "#s": "status",
                },
                ExpressionAttributeValues={
                    ":status": "processing",
                    ":analysisVersion": "interview-prep-queued-v1",
                },
            )

            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({
                    "jobType": "interviewPreparation",
                    "interviewPrepId": interview_prep_id
                })
            )
        
        logger.info("Completed job match: %s", str(match_id))


def process_resume_tailoring(tailoring_id):
    logger.info("Starting resume tailoring: %s", str(tailoring_id))
    tailoring_item = get_entity_by_id(tailoring_id, "resumeTailoring")

    if not tailoring_item:
        logger.info("Raised ValueError since tailoring not found for interview prep: %s", str(interview_prep_id))
        raise ValueError(f"Resume tailoring not found: {tailoring_id}")

    resume_text = tailoring_item.get("resumeText", "").strip()
    job_description_text = tailoring_item.get("jobDescriptionText", "").strip()

    if not resume_text:
        logger.info("Raised ValueError since resumeText not found for interview prep: %s", str(interview_prep_id))
        raise ValueError(f"No resumeText found for tailoring: {tailoring_id}")

    if not job_description_text:
        logger.info("Raised ValueError since jobDescriptionText not found for interview prep: %s", str(interview_prep_id))
        raise ValueError(f"No jobDescriptionText found for tailoring: {tailoring_id}")

    requested_provider = tailoring_item.get("provider") or os.getenv("ANALYSIS_PROVIDER", "rule-based")

    started = time.perf_counter()

    provider = get_analysis_provider(requested_provider)
    tailoring_result = provider.tailor_resume(resume_text, job_description_text)

    duration_ms = int((time.perf_counter() - started) * 1000)

    table.update_item(
        Key={"pk": item["pk"], "sk": item["sk"]},
        UpdateExpression="""
            SET #s = :status,
                provider = :provider,
                model = :model,
                analysisVersion = :analysisVersion,
                analysisDurationMs = :analysisDurationMs,
                tailoredExecutiveSummary = :tailoredExecutiveSummary,
                tailoredResumeBullets = :tailoredResumeBullets,
                keywordsToAdd = :keywordsToAdd,
                rolePositioningAdvice = :rolePositioningAdvice,
                atsOptimizationAdvice = :atsOptimizationAdvice,
                rewriteWarnings = :rewriteWarnings,
                completedAt = :completedAt
        """,
        ExpressionAttributeNames={
            "#s": "status",
        },
        ExpressionAttributeValues=to_dynamodb_value(
            {
                ":status": "completed",
                ":provider": tailoring_result["provider"],
                ":model": tailoring_result.get("model", ""),
                ":analysisVersion": tailoring_result["analysisVersion"],
                ":analysisDurationMs": duration_ms,
                ":tailoredExecutiveSummary": tailoring_result.get("tailoredExecutiveSummary", ""),
                ":tailoredResumeBullets": tailoring_result.get("tailoredResumeBullets", []),
                ":keywordsToAdd": tailoring_result.get("keywordsToAdd", []),
                ":rolePositioningAdvice": tailoring_result.get("rolePositioningAdvice", []),
                ":atsOptimizationAdvice": tailoring_result.get("atsOptimizationAdvice", []),
                ":rewriteWarnings": tailoring_result.get("rewriteWarnings", []),
                ":completedAt": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )
    logger.info("Completed interview prep: %s", str(tailoring_id))


def process_interview_preparation(interview_prep_id):
    logger.info("Starting interview prep: %s", str(interview_prep_id))
    item = get_entity_by_id(interview_prep_id, "interviewPreparation")

    if not item:
        logger.info("Raised ValueError since Interview preparation not found: %s", str(interview_prep_id))
        raise ValueError(f"Interview preparation not found: {interview_prep_id}")

    resume_text = item.get("resumeText", "").strip()
    job_description_text = item.get("jobDescriptionText", "").strip()

    if not resume_text:
        logger.info("Raised ValueError since resumeText was not found for interview prep: %s", str(interview_prep_id))
        raise ValueError(f"No resumeText found for interview prep: {interview_prep_id}")

    if not job_description_text:
        logger.info("Raised ValueError since jobDescriptionText was not found for interview prep: %s", str(interview_prep_id))
        raise ValueError(f"No jobDescriptionText found for interview prep: {interview_prep_id}")

    requested_provider = item.get("provider") or os.getenv("ANALYSIS_PROVIDER", "rule-based")

    started = time.perf_counter()

    provider = get_analysis_provider(requested_provider)
    prep_result = provider.prepare_interview(resume_text, job_description_text)

    duration_ms = int((time.perf_counter() - started) * 1000)

    table.update_item(
        Key={"pk": item["pk"], "sk": item["sk"]},
        UpdateExpression="""
            SET #s = :status,
                provider = :provider,
                model = :model,
                analysisVersion = :analysisVersion,
                analysisDurationMs = :analysisDurationMs,
                behavioralQuestions = :behavioralQuestions,
                leadershipQuestions = :leadershipQuestions,
                systemDesignQuestions = :systemDesignQuestions,
                cloudArchitectureQuestions = :cloudArchitectureQuestions,
                securityQuestions = :securityQuestions,
                resumeSpecificQuestions = :resumeSpecificQuestions,
                jobSpecificQuestions = :jobSpecificQuestions,
                interviewReadinessSummary = :interviewReadinessSummary,
                completedAt = :completedAt
        """,
        ExpressionAttributeNames={
            "#s": "status",
        },
        ExpressionAttributeValues=to_dynamodb_value(
            {
                ":status": "completed",
                ":provider": prep_result["provider"],
                ":model": prep_result.get("model", ""),
                ":analysisVersion": prep_result["analysisVersion"],
                ":analysisDurationMs": duration_ms,
                ":behavioralQuestions": prep_result.get("behavioralQuestions", []),
                ":leadershipQuestions": prep_result.get("leadershipQuestions", []),
                ":systemDesignQuestions": prep_result.get("systemDesignQuestions", []),
                ":cloudArchitectureQuestions": prep_result.get("cloudArchitectureQuestions", []),
                ":securityQuestions": prep_result.get("securityQuestions", []),
                ":resumeSpecificQuestions": prep_result.get("resumeSpecificQuestions", []),
                ":jobSpecificQuestions": prep_result.get("jobSpecificQuestions", []),
                ":interviewReadinessSummary": prep_result.get("interviewReadinessSummary", ""),
                ":completedAt": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )
    logger.info("Completed interview prep: %s", str(interview_prep_id))


def entity_gsi_pk(entity_id):
    return f"ENTITY#{entity_id}"


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


def lambda_handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record["body"])

        job_type = body.get("jobType", "resumeAnalysis")

        try:
            if job_type == "jobMatch":
                process_job_match(body["matchId"])
            elif job_type == "resumeTailoring":
                process_resume_tailoring(body["tailoringId"])
            elif job_type == "interviewPreparation":
                process_interview_preparation(body["interviewPrepId"])
            else:
                process_resume_analysis(body["analysisId"])

        except Exception as error:
            record_id = body.get("matchId") or body.get("analysisId")

            expected_record_type = None

            if job_type == "resumeAnalysis":
                expected_record_type = "resumeAnalysis"
            elif job_type == "jobMatch":
                expected_record_type = "jobMatch"
            elif job_type == "resumeTailoring":
                expected_record_type = "resumeTailoring"
            elif job_type == "interviewPreparation":
                expected_record_type = "interviewPreparation"

            update_record_failed(record_id, str(error), expected_record_type)
            raise

    return {"status": "ok"}


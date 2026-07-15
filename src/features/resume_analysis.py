import logging
import os
import uuid
import time 
from datetime import datetime, timezone
from io import BytesIO

from pypdf import PdfReader

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# imports from project specific files
from providers.factory import get_analysis_provider
from core.responses import build_response, parse_body
from core.auth import current_user_id, assert_item_owner
from core.errors import ResourceConflictError
from core.keys import base_keys, resume_sk, user_pk
from core.outbox import build_resume_analysis_outbox_event
from core.storage import (
    document_bucket,
    get_entity_by_id,
    s3,
    table,
    put_item_and_outbox_if_absent,
    put_item_if_absent,
)
from core.idempotency import (
    DISPOSITION_REPLAY_COMPLETED,
    DISPOSITION_REPLAY_IN_PROGRESS,
    complete_request,
    mark_request_retryable,
    request_fingerprint,
    reserve_request,
)
from core.request_context import build_request_context
from features.target_career import get_target_career_for_user


logger = logging.getLogger(__name__)


ANALYZE_RESUME_OPERATION = "ANALYZE_RESUME"
CREATE_RESUME_UPLOAD_URL_OPERATION = "CREATE_RESUME_UPLOAD_URL"
ANALYZE_UPLOADED_RESUME_OPERATION = "ANALYZE_UPLOADED_RESUME"


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def analyze_and_save_resume(
    *,
    user_id,
    analysis_id,
    request_id,
    request_hash,
    region,
    resume_text,
    source_type,
    target_career,
    document_bucket_name="",
    document_key="",
    file_name="",
    requested_provider=None,
    resume_name="Untitled Resume",
):
    analysis_started = time.perf_counter()
    resume_text = str(resume_text or "").strip()

    if not resume_text:
        raise ValueError("No resume text could be analyzed")

    analysis_key = {
        "pk": user_pk(user_id),
        "sk": resume_sk(analysis_id),
    }

    existing = table.get_item(
        Key=analysis_key,
        ConsistentRead=True,
    ).get("Item")

    created_at = datetime.now(timezone.utc).isoformat()

    if existing:
        if existing.get("createdByRequestHash") != request_hash:
            raise RuntimeError(
                "Analysis identifier already exists"
            )

        if existing.get("status") == "completed":
            return existing

        created_at = existing.get("createdAt", created_at)

    else:
        pending_item = {
            **base_keys(
                pk=analysis_key["pk"],
                sk=analysis_key["sk"],
                entity_id=analysis_id,
                record_type="resumeAnalysis",
            ),
            "recordType": "resumeAnalysis",
            "userId": user_id,
            "analysisId": analysis_id,
            "createdAt": created_at,
            "updatedAt": created_at,
            "createdByRequestId": request_id,
            "updatedByRequestId": request_id,
            "createdByRequestHash": request_hash,
            "createdRegion": region,
            "lastUpdatedRegion": region,
            "version": 1,
            "sourceType": source_type,
            "status": "ANALYSIS_IN_PROGRESS",
            "provider": (
                requested_provider
                or os.getenv(
                    "ANALYSIS_PROVIDER",
                    "rule-based",
                )
            ),
            "model": os.getenv("OPENAI_MODEL", ""),
            "analysisVersion": "text-analysis-pending-v2",
            "analysisDurationMs": 0,
            "score": 0,
            "wordCount": len(resume_text.split()),
            "resumeName": resume_name,
            "resumeText": resume_text,
            "strengths": [],
            "recommendations": [],
            "executiveSummary": "",
            "documentBucket": document_bucket_name,
            "documentKey": document_key,
            "fileName": file_name,
            "targetCareer": target_career,
            "targetRoleTitle": target_career.get(
                "roleTitle",
                "",
            ),
            "targetIndustry": target_career.get(
                "industry",
                "",
            ),
            "dynamicScores": [],
            "roleFitSummary": "",
            "roleSpecificGaps": [],
        }

        if not put_item_if_absent(pending_item):
            existing = table.get_item(
                Key=analysis_key,
                ConsistentRead=True,
            ).get("Item")

            if (
                not existing
                or existing.get("createdByRequestHash")
                != request_hash
            ):
                raise RuntimeError(
                    "Analysis identifier already exists"
                )

            if existing.get("status") == "completed":
                return existing

            created_at = existing.get(
                "createdAt",
                created_at,
            )

    provider = get_analysis_provider(requested_provider)

    analysis_result = provider.analyze(
        resume_text,
        target_career,
    )

    analysis_duration_ms = int(
        (time.perf_counter() - analysis_started) * 1000
    )
    completed_at = datetime.now(timezone.utc).isoformat()

    response = table.update_item(
        Key=analysis_key,
        UpdateExpression=(
            "SET #status = :completed, "
            "updatedAt = :updatedAt, "
            "updatedByRequestId = :requestId, "
            "lastUpdatedRegion = :region, "
            "provider = :provider, "
            "model = :model, "
            "analysisVersion = :analysisVersion, "
            "analysisDurationMs = :analysisDurationMs, "
            "score = :score, "
            "wordCount = :wordCount, "
            "strengths = :strengths, "
            "recommendations = :recommendations, "
            "executiveSummary = :executiveSummary, "
            "dynamicScores = :dynamicScores, "
            "roleFitSummary = :roleFitSummary, "
            "roleSpecificGaps = :roleSpecificGaps, "
            "#version = if_not_exists(#version, :zero) + :one"
        ),
        ConditionExpression=(
            "#status = :inProgress "
            "AND createdByRequestHash = :requestHash"
        ),
        ExpressionAttributeNames={
            "#status": "status",
            "#version": "version",
        },
        ExpressionAttributeValues={
            ":completed": "completed",
            ":inProgress": "ANALYSIS_IN_PROGRESS",
            ":updatedAt": completed_at,
            ":requestId": request_id,
            ":region": region,
            ":provider": analysis_result["provider"],
            ":model": analysis_result.get("model", ""),
            ":analysisVersion": analysis_result[
                "analysisVersion"
            ],
            ":analysisDurationMs": analysis_duration_ms,
            ":score": analysis_result["score"],
            ":wordCount": analysis_result["wordCount"],
            ":strengths": analysis_result["strengths"],
            ":recommendations": analysis_result[
                "recommendations"
            ],
            ":executiveSummary": analysis_result.get(
                "executiveSummary",
                "",
            ),
            ":dynamicScores": analysis_result.get(
                "dynamicScores",
                [],
            ),
            ":roleFitSummary": analysis_result.get(
                "roleFitSummary",
                "",
            ),
            ":roleSpecificGaps": analysis_result.get(
                "roleSpecificGaps",
                [],
            ),
            ":requestHash": request_hash,
            ":zero": 0,
            ":one": 1,
        },
        ReturnValues="ALL_NEW",
    )

    return response["Attributes"]


def analyze_resume(event):
    body = parse_body(event)

    if body is None:
        return build_response(
            400,
            {"error": "Invalid JSON body"},
        )

    context = build_request_context(
        event,
        require_idempotency=True,
    )
    user_id = context.user_id

    resume_name = (
        str(body.get("resumeName") or "").strip()
        or "Untitled Resume"
    )
    resume_text = str(
        body.get("resumeText") or ""
    ).strip()
    requested_provider = (
        body.get("analysisProvider")
        or os.getenv(
            "ANALYSIS_PROVIDER",
            "rule-based",
        )
    )

    if not resume_text:
        return build_response(
            400,
            {"error": "resumeText is required"},
        )

    target_career = get_target_career_for_user(user_id)

    if not target_career:
        return build_response(
            400,
            {
                "error": (
                    "Target Career is required before "
                    "analyzing resumes"
                )
            },
        )

    request_hash = request_fingerprint(
        user_id=user_id,
        operation=ANALYZE_RESUME_OPERATION,
        body={
            "resumeName": resume_name,
            "resumeText": resume_text,
            "analysisProvider": requested_provider,
        },
    )

    proposed_analysis_id = str(uuid.uuid4())

    reservation = reserve_request(
        user_id=user_id,
        operation=ANALYZE_RESUME_OPERATION,
        idempotency_key=context.idempotency_key,
        request_hash=request_hash,
        resource_id=proposed_analysis_id,
        request_id=context.request_id,
        region=context.region,
    )

    if reservation.disposition == DISPOSITION_REPLAY_COMPLETED:
        return build_response(
            reservation.status_code or 200,
            reservation.response_body or {},
        )

    if reservation.disposition == DISPOSITION_REPLAY_IN_PROGRESS:
        return build_response(
            reservation.status_code or 202,
            reservation.response_body
            or {
                "analysisId": reservation.resource_id,
                "status": "ANALYSIS_IN_PROGRESS",
            },
        )

    analysis_id = reservation.resource_id

    try:
        item = analyze_and_save_resume(
            user_id=user_id,
            analysis_id=analysis_id,
            request_id=context.request_id,
            request_hash=request_hash,
            region=context.region,
            resume_text=resume_text,
            source_type="text",
            requested_provider=requested_provider,
            resume_name=resume_name,
            target_career=target_career,
        )

        response_body = {
            "analysisId": analysis_id,
            "status": item.get("status", "completed"),
            "version": int(item.get("version", 1)),
            "sourceType": "text",
            "resumeName": item.get(
                "resumeName",
                resume_name,
            ),
            "createdAt": item.get("createdAt", ""),
            "provider": item.get("provider", ""),
            "model": item.get("model", ""),
            "analysisVersion": item.get(
                "analysisVersion",
                "",
            ),
            "analysisDurationMs": item.get(
                "analysisDurationMs",
                0,
            ),
            "score": item.get("score", 0),
            "wordCount": item.get("wordCount", 0),
            "strengths": item.get("strengths", []),
            "recommendations": item.get(
                "recommendations",
                [],
            ),
            "executiveSummary": item.get(
                "executiveSummary",
                "",
            ),
            "targetRoleTitle": item.get(
                "targetRoleTitle",
                "",
            ),
            "targetIndustry": item.get(
                "targetIndustry",
                "",
            ),
            "dynamicScores": item.get(
                "dynamicScores",
                [],
            ),
            "roleFitSummary": item.get(
                "roleFitSummary",
                "",
            ),
            "roleSpecificGaps": item.get(
                "roleSpecificGaps",
                [],
            ),
        }

        complete_request(
            user_id=user_id,
            operation=ANALYZE_RESUME_OPERATION,
            idempotency_key=context.idempotency_key,
            request_hash=request_hash,
            resource_id=analysis_id,
            request_id=context.request_id,
            region=context.region,
            status_code=200,
            response_body=response_body,
        )

        return build_response(200, response_body)

    except Exception:
        logger.exception(
            "Synchronous resume analysis failed",
            extra={
                "analysisId": analysis_id,
                "requestId": context.request_id,
                "region": context.region,
            },
        )

        try:
            mark_request_retryable(
                user_id=user_id,
                operation=ANALYZE_RESUME_OPERATION,
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
                resource_id=analysis_id,
                request_id=context.request_id,
                region=context.region,
            )
        except Exception:
            logger.exception(
                "Could not mark text analysis retryable",
                extra={
                    "analysisId": analysis_id,
                    "requestId": context.request_id,
                },
            )

        raise


def create_resume_upload_url(event):
    body = parse_body(event)

    if body is None:
        return build_response(
            400,
            {"error": "Invalid JSON body"},
        )

    context = build_request_context(
        event,
        require_idempotency=True,
    )
    user_id = context.user_id

    file_name = str(
        body.get("fileName") or ""
    ).strip()
    content_type = str(
        body.get("contentType")
        or "application/pdf"
    ).strip()

    if not file_name:
        return build_response(
            400,
            {"error": "fileName is required"},
        )

    if content_type != "application/pdf":
        return build_response(
            400,
            {
                "error": (
                    "Only application/pdf uploads "
                    "are currently supported"
                )
            },
        )

    request_hash = request_fingerprint(
        user_id=user_id,
        operation=CREATE_RESUME_UPLOAD_URL_OPERATION,
        body={
            "fileName": file_name,
            "contentType": content_type,
        },
    )

    proposed_upload_id = str(uuid.uuid4())

    reservation = reserve_request(
        user_id=user_id,
        operation=CREATE_RESUME_UPLOAD_URL_OPERATION,
        idempotency_key=context.idempotency_key,
        request_hash=request_hash,
        resource_id=proposed_upload_id,
        request_id=context.request_id,
        region=context.region,
    )

    upload_id = reservation.resource_id
    document_key = (
        f"uploads/{user_id}/{upload_id}/{file_name}"
    )

    try:
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": document_bucket,
                "Key": document_key,
                "ContentType": content_type,
            },
            ExpiresIn=900,
        )

        response_body = {
            "uploadId": upload_id,
            "uploadUrl": upload_url,
            "documentBucket": document_bucket,
            "documentKey": document_key,
            "fileName": file_name,
            "contentType": content_type,
            "expiresInSeconds": 900,
        }

        if (
            reservation.disposition
            != DISPOSITION_REPLAY_COMPLETED
        ):
            complete_request(
                user_id=user_id,
                operation=(
                    CREATE_RESUME_UPLOAD_URL_OPERATION
                ),
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
                resource_id=upload_id,
                request_id=context.request_id,
                region=context.region,
                status_code=200,
                response_body={
                    "uploadId": upload_id,
                    "documentBucket": document_bucket,
                    "documentKey": document_key,
                    "fileName": file_name,
                    "contentType": content_type,
                    "expiresInSeconds": 900,
                },
            )

        return build_response(200, response_body)

    except Exception:
        logger.exception(
            "Resume upload URL creation failed",
            extra={
                "uploadId": upload_id,
                "requestId": context.request_id,
                "region": context.region,
            },
        )

        try:
            mark_request_retryable(
                user_id=user_id,
                operation=(
                    CREATE_RESUME_UPLOAD_URL_OPERATION
                ),
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
                resource_id=upload_id,
                request_id=context.request_id,
                region=context.region,
            )
        except Exception:
            logger.exception(
                "Could not mark upload request retryable",
                extra={
                    "uploadId": upload_id,
                    "requestId": context.request_id,
                },
            )

        raise


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

    context = build_request_context(
        event,
        require_idempotency=True,
    )
    user_id = context.user_id

    target_career = get_target_career_for_user(user_id)

    if not target_career:
        return build_response(
            400,
            {
                "error": (
                    "Target Career is required before analyzing resumes"
                )
            },
        )

    file_name = str(body.get("fileName") or "").strip()
    resume_name = (
        str(body.get("resumeName") or "").strip()
        or file_name
        or "Untitled Resume"
    )
    document_key = str(body.get("documentKey") or "").strip()

    if not document_key:
        return build_response(
            400,
            {"error": "documentKey is required"},
        )

    supplied_bucket = str(
        body.get("documentBucket") or document_bucket
    ).strip()

    if supplied_bucket != document_bucket:
        return build_response(
            400,
            {"error": "Invalid document bucket"},
        )

    bucket_name = document_bucket

    requested_provider = (
        body.get("analysisProvider")
        or os.getenv("ANALYSIS_PROVIDER", "rule-based")
    )

    fingerprint_body = {
        "documentBucket": bucket_name,
        "documentKey": document_key,
        "fileName": file_name,
        "resumeName": resume_name,
        "analysisProvider": requested_provider,
    }

    request_hash = request_fingerprint(
        user_id=user_id,
        operation=ANALYZE_UPLOADED_RESUME_OPERATION,
        body=fingerprint_body,
    )

    proposed_analysis_id = str(uuid.uuid4())

    reservation = reserve_request(
        user_id=user_id,
        operation=ANALYZE_UPLOADED_RESUME_OPERATION,
        idempotency_key=context.idempotency_key,
        request_hash=request_hash,
        resource_id=proposed_analysis_id,
        request_id=context.request_id,
        region=context.region,
    )

    if reservation.disposition == DISPOSITION_REPLAY_COMPLETED:
        return build_response(
            reservation.status_code or 202,
            reservation.response_body or {},
        )

    if reservation.disposition == DISPOSITION_REPLAY_IN_PROGRESS:
        return build_response(
            reservation.status_code or 202,
            reservation.response_body
            or {
                "analysisId": reservation.resource_id,
                "status": "processing",
            },
        )

    analysis_id = reservation.resource_id

    try:
        analysis_key = {
            "pk": user_pk(user_id),
            "sk": resume_sk(analysis_id),
        }

        existing = table.get_item(
            Key=analysis_key,
            ConsistentRead=True,
        ).get("Item")

        if existing:
            if existing.get("createdByRequestHash") != request_hash:
                raise RuntimeError(
                    "Analysis identifier already exists"
                )

            item = existing
            created_at = existing.get(
                "createdAt",
                datetime.now(timezone.utc).isoformat(),
            )
        else:
            extracted_text = extract_text_from_pdf(
                bucket_name,
                document_key,
            )

            if not extracted_text:
                response_body = {
                    "error": (
                        "No resume text could be extracted from PDF"
                    ),
                    "analysisId": analysis_id,
                }

                complete_request(
                    user_id=user_id,
                    operation=ANALYZE_UPLOADED_RESUME_OPERATION,
                    idempotency_key=context.idempotency_key,
                    request_hash=request_hash,
                    resource_id=analysis_id,
                    request_id=context.request_id,
                    region=context.region,
                    status_code=400,
                    response_body=response_body,
                )

                return build_response(400, response_body)

            created_at = datetime.now(timezone.utc).isoformat()

            item = {
                **base_keys(
                    pk=analysis_key["pk"],
                    sk=analysis_key["sk"],
                    entity_id=analysis_id,
                    record_type="resumeAnalysis",
                ),
                "recordType": "resumeAnalysis",
                "userId": user_id,
                "analysisId": analysis_id,
                "createdAt": created_at,
                "updatedAt": created_at,
                "createdByRequestId": context.request_id,
                "updatedByRequestId": context.request_id,
                "createdByRequestHash": request_hash,
                "createdRegion": context.region,
                "lastUpdatedRegion": context.region,
                "version": 1,
                "sourceType": "pdf",
                "status": "QUEUED_PENDING_DISPATCH",
                "provider": requested_provider,
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
                    "Resume is queued for AI analysis",
                ],
                "recommendations": [
                    "AI analysis is queued for asynchronous processing."
                ],
                "executiveSummary": (
                    "PDF text was extracted and saved. "
                    "AI analysis is pending."
                ),
                "documentBucket": bucket_name,
                "documentKey": document_key,
                "fileName": file_name,
                "requestedProvider": requested_provider,
                "targetCareer": target_career,
                "targetRoleTitle": target_career.get(
                    "roleTitle",
                    "",
                ),
                "targetIndustry": target_career.get(
                    "industry",
                    "",
                ),
                "dynamicScores": [],
                "roleFitSummary": "",
                "roleSpecificGaps": [],
            }

            outbox_event = build_resume_analysis_outbox_event(
                analysis_id=analysis_id,
                user_id=user_id,
                analysis_provider=requested_provider,
                created_region=context.region,
                request_id=context.request_id,
                created_at=created_at,
            )

            created = put_item_and_outbox_if_absent(
                item=item,
                outbox_item=outbox_event.item,
            )

            if not created:
                existing = table.get_item(
                    Key=analysis_key,
                    ConsistentRead=True,
                ).get("Item")

                if (
                    not existing
                    or existing.get("createdByRequestHash")
                    != request_hash
                ):
                    raise RuntimeError(
                        "Analysis identifier already exists"
                    )

                item = existing
                created_at = existing.get(
                    "createdAt",
                    created_at,
                )

        current_status = item.get("status")

        if current_status not in {
            "QUEUED_PENDING_DISPATCH",
            "processing",
            "WORKER_PROCESSING",
            "completed",
            "FAILED_RETRYABLE",
        }:
            raise RuntimeError(
                "Analysis is in an unsupported dispatch state"
            )

        response_body = {
            "analysisId": analysis_id,
            "status": current_status,
            "version": int(item.get("version", 1)),
            "resumeName": item.get(
                "resumeName",
                resume_name,
            ),
            "createdAt": item.get(
                "createdAt",
                created_at,
            ),
            "sourceType": "pdf",
        }

        complete_request(
            user_id=user_id,
            operation=ANALYZE_UPLOADED_RESUME_OPERATION,
            idempotency_key=context.idempotency_key,
            request_hash=request_hash,
            resource_id=analysis_id,
            request_id=context.request_id,
            region=context.region,
            status_code=202,
            response_body=response_body,
        )

        return build_response(202, response_body)

    except Exception:
        logger.exception(
            "Uploaded resume analysis submission failed",
            extra={
                "analysisId": analysis_id,
                "requestId": context.request_id,
                "region": context.region,
            },
        )

        try:
            mark_request_retryable(
                user_id=user_id,
                operation=ANALYZE_UPLOADED_RESUME_OPERATION,
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
                resource_id=analysis_id,
                request_id=context.request_id,
                region=context.region,
            )
        except Exception:
            logger.exception(
                "Could not mark idempotency request retryable",
                extra={
                    "analysisId": analysis_id,
                    "requestId": context.request_id,
                    "region": context.region,
                },
            )

        raise


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
    context = build_request_context(event)
    user_id = context.user_id

    analysis_id = event.get(
        "pathParameters",
        {},
    ).get("id")

    if not analysis_id:
        return build_response(
            400,
            {"error": "analysis id is required"},
        )

    query_parameters = (
        event.get("queryStringParameters") or {}
    )

    try:
        expected_version = int(
            query_parameters.get("version")
        )
    except (TypeError, ValueError):
        return build_response(
            400,
            {
                "error": (
                    "version query parameter is required "
                    "and must be an integer"
                )
            },
        )

    if expected_version < 0:
        return build_response(
            400,
            {"error": "version must be zero or greater"},
        )

    analysis_key = {
        "pk": user_pk(user_id),
        "sk": resume_sk(analysis_id),
    }

    existing = table.get_item(
        Key=analysis_key,
        ConsistentRead=True,
    ).get("Item")

    if not existing:
        return build_response(
            404,
            {"error": "analysis not found"},
        )

    try:
        table.delete_item(
            Key=analysis_key,
            ConditionExpression=(
                "userId = :userId "
                "AND recordType = :recordType "
                "AND ("
                "#version = :expectedVersion "
                "OR ("
                "attribute_not_exists(#version) "
                "AND :expectedVersion = :zero"
                ")"
                ")"
            ),
            ExpressionAttributeNames={
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":userId": user_id,
                ":recordType": "resumeAnalysis",
                ":expectedVersion": expected_version,
                ":zero": 0,
            },
        )
    except ClientError as error:
        if is_conditional_failure(error):
            raise ResourceConflictError(
                (
                    "The resume analysis changed before "
                    "it could be deleted"
                )
            )

        raise

    return build_response(
        200,
        {
            "deleted": True,
            "analysisId": analysis_id,
            "deletedVersion": expected_version,
        },
    )


def delete_all_analyses(event):
    context = build_request_context(event)
    user_id = context.user_id

    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq(user_pk(user_id))
            & Key("sk").begins_with("RESUME#")
        ),
        ConsistentRead=True,
    )

    analyses = response.get("Items", [])

    requested = len(analyses)
    deleted = 0
    conflicted = 0
    failed = 0

    for item in analyses:
        expected_version = int(item.get("version", 0))

        try:
            table.delete_item(
                Key={
                    "pk": item["pk"],
                    "sk": item["sk"],
                },
                ConditionExpression=(
                    "userId = :userId "
                    "AND recordType = :recordType "
                    "AND ("
                    "#version = :expectedVersion "
                    "OR ("
                    "attribute_not_exists(#version) "
                    "AND :expectedVersion = :zero"
                    ")"
                    ")"
                ),
                ExpressionAttributeNames={
                    "#version": "version",
                },
                ExpressionAttributeValues={
                    ":userId": user_id,
                    ":recordType": "resumeAnalysis",
                    ":expectedVersion": expected_version,
                    ":zero": 0,
                },
            )

            deleted += 1

        except ClientError as error:
            if is_conditional_failure(error):
                conflicted += 1
                continue

            logger.exception(
                "Bulk resume-analysis deletion failed",
                extra={
                    "analysisId": item.get("analysisId"),
                    "requestId": context.request_id,
                    "region": context.region,
                },
            )

            failed += 1

    return build_response(
        200,
        {
            "requested": requested,
            "deleted": deleted,
            "conflicted": conflicted,
            "failed": failed,
            "recordType": "resumeAnalysis",
        },
    )
    

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

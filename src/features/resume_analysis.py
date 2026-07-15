import json
import logging
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

ANALYZE_UPLOADED_RESUME_OPERATION = "ANALYZE_UPLOADED_RESUME"


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

            created = put_item_if_absent(item)

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

        if current_status == "QUEUED_PENDING_DISPATCH":
            sqs.send_message(
                QueueUrl=resume_analysis_queue_url,
                MessageBody=json.dumps(
                    {
                        "schemaVersion": 1,
                        "jobType": "resumeAnalysis",
                        "operation": (
                            ANALYZE_UPLOADED_RESUME_OPERATION
                        ),
                        "jobId": analysis_id,
                        "analysisId": analysis_id,
                        "userId": user_id,
                        "sourceType": "pdf",
                        "analysisProvider": requested_provider,
                        "requestId": context.request_id,
                        "requestHash": request_hash,
                        "sourceRegion": context.region,
                        "submittedAt": created_at,
                    }
                ),
            )

            update_response = table.update_item(
                Key=analysis_key,
                UpdateExpression=(
                    "SET #status = :processing, "
                    "updatedAt = :updatedAt, "
                    "updatedByRequestId = :requestId, "
                    "lastUpdatedRegion = :region, "
                    "#version = #version + :one"
                ),
                ConditionExpression=(
                    "#status = :pendingDispatch "
                    "AND createdByRequestHash = :requestHash"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#version": "version",
                },
                ExpressionAttributeValues={
                    ":pendingDispatch": (
                        "QUEUED_PENDING_DISPATCH"
                    ),
                    ":processing": "processing",
                    ":requestHash": request_hash,
                    ":updatedAt": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    ":requestId": context.request_id,
                    ":region": context.region,
                    ":one": 1,
                },
                ReturnValues="ALL_NEW",
            )

            item = update_response.get("Attributes", item)
            current_status = item.get("status", "processing")

        elif current_status not in {
            "processing",
            "completed",
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

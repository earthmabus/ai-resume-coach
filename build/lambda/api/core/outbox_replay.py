from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Sequence

import boto3
from botocore.exceptions import ClientError

from core.keys import (
    outbox_pk,
    outbox_sk,
    outbox_status_pk,
    outbox_status_sk,
)
from core.outbox import (
    OUTBOX_STATUS_FAILED_PERMANENT,
    OUTBOX_STATUS_PENDING,
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def replay_event(
    *,
    table: Any,
    event_id: str,
    operator: str,
    now: str | None = None,
) -> dict[str, Any]:
    normalized_event_id = str(
        event_id or ""
    ).strip()

    if not normalized_event_id:
        raise ValueError(
            "event_id is required"
        )

    normalized_operator = str(
        operator or ""
    ).strip()

    if not normalized_operator:
        raise ValueError(
            "operator is required"
        )

    key = {
        "pk": outbox_pk(
            normalized_event_id
        ),
        "sk": outbox_sk(
            normalized_event_id
        ),
    }

    existing = table.get_item(
        Key=key,
        ConsistentRead=True,
    ).get("Item")

    if not existing:
        raise LookupError(
            "Outbox event "
            f"{normalized_event_id} "
            "was not found"
        )

    if (
        existing.get("status")
        != OUTBOX_STATUS_FAILED_PERMANENT
    ):
        raise ValueError(
            "Only FAILED_PERMANENT outbox "
            "events may be replayed"
        )

    created_at = str(
        existing.get("createdAt") or ""
    ).strip()

    if not created_at:
        raise ValueError(
            "Outbox event createdAt is required"
        )

    timestamp = now or utc_now()

    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=(
                "SET #status = :pending, "
                "gsi1pk = :pendingPk, "
                "gsi1sk = :gsi1sk, "
                "deliveryAttempts = :zero, "
                "replayCount = "
                "if_not_exists("
                "replayCount, :zero"
                ") + :one, "
                "replayedAt = :now, "
                "replayedBy = :operator, "
                "updatedAt = :now, "
                "updatedByRequestId = "
                ":operator, "
                "#version = "
                "if_not_exists("
                "#version, :zero"
                ") + :one "
                "REMOVE permanentlyFailedAt, "
                "lastDeliveryError, "
                "lastDeliveryFailedAt, "
                "nextDeliveryAttemptAt, "
                "dispatchAttemptId, "
                "dispatchStartedAt, "
                "dispatchLeaseExpiresAt, "
                "transportMessageId, "
                "deliveredAt, "
                "expiresAt"
            ),
            ConditionExpression=(
                "#status = :failedPermanent"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":pending": (
                    OUTBOX_STATUS_PENDING
                ),
                ":pendingPk": (
                    outbox_status_pk(
                        OUTBOX_STATUS_PENDING
                    )
                ),
                ":gsi1sk": (
                    outbox_status_sk(
                        created_at=created_at,
                        event_id=(
                            normalized_event_id
                        ),
                    )
                ),
                ":failedPermanent": (
                    OUTBOX_STATUS_FAILED_PERMANENT
                ),
                ":operator": (
                    normalized_operator
                ),
                ":now": timestamp,
                ":zero": 0,
                ":one": 1,
            },
            ReturnValues="ALL_NEW",
        )

    except ClientError as error:
        if (
            error.response.get(
                "Error",
                {},
            ).get("Code")
            == (
                "ConditionalCheckFailedException"
            )
        ):
            raise RuntimeError(
                "The event changed before "
                "it could be replayed"
            ) from error

        raise

    return response["Attributes"]


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Move one FAILED_PERMANENT "
            "outbox event back to PENDING."
        )
    )

    parser.add_argument(
        "--event-id",
        required=True,
    )

    parser.add_argument(
        "--table-name",
        default=os.getenv(
            "RESUME_ANALYSIS_TABLE",
            "",
        ),
    )

    parser.add_argument(
        "--region",
        default=os.getenv(
            "AWS_REGION",
            os.getenv(
                "AWS_DEFAULT_REGION",
                "us-east-1",
            ),
        ),
    )

    parser.add_argument(
        "--operator",
        default=os.getenv(
            "USER",
            "outbox-operator",
        ),
    )

    args = parser.parse_args(argv)

    if not str(
        args.table_name or ""
    ).strip():
        parser.error(
            "--table-name or "
            "RESUME_ANALYSIS_TABLE "
            "is required"
        )

    return args


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = parse_args(argv)

    table = boto3.resource(
        "dynamodb",
        region_name=args.region,
    ).Table(
        args.table_name
    )

    try:
        item = replay_event(
            table=table,
            event_id=args.event_id,
            operator=args.operator,
        )

    except (
        LookupError,
        ValueError,
        RuntimeError,
        ClientError,
    ) as error:
        print(
            str(error),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "eventId": item.get(
                    "eventId",
                    args.event_id,
                ),
                "status": item.get(
                    "status"
                ),
                "replayCount": int(
                    item.get(
                        "replayCount",
                        0,
                    )
                ),
                "replayedAt": item.get(
                    "replayedAt"
                ),
                "replayedBy": item.get(
                    "replayedBy"
                ),
            },
            separators=(",", ":"),
        )
    )

    return 0

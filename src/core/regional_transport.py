from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Protocol

from botocore.exceptions import BotoCoreError, ClientError

from core.region_routing import normalize_region


class DeliveryStatus(str, Enum):
    NOOP_LOCAL = "NOOP_LOCAL"
    DELIVERED = "DELIVERED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    UNSUPPORTED_REGION = "UNSUPPORTED_REGION"
    INVALID_PLACEMENT = "INVALID_PLACEMENT"


@dataclass(frozen=True)
class RegionalDeliveryRequest:
    current_region: str
    owner_region: str
    payload: Mapping[str, Any]
    request_id: str
    delivery_type: str
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        current_region = normalize_region(self.current_region)
        owner_region = normalize_region(self.owner_region)
        request_id = str(self.request_id or "").strip()
        delivery_type = str(self.delivery_type or "").strip()

        if not current_region:
            raise ValueError("current_region must not be blank")

        if not owner_region:
            raise ValueError("owner_region must not be blank")

        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")

        if not request_id:
            raise ValueError("request_id must not be blank")

        if not delivery_type:
            raise ValueError("delivery_type must not be blank")

        object.__setattr__(self, "current_region", current_region)
        object.__setattr__(self, "owner_region", owner_region)
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "delivery_type", delivery_type)
        object.__setattr__(
            self,
            "correlation_id",
            (
                str(self.correlation_id or "").strip()
                or None
            ),
        )


@dataclass(frozen=True)
class RegionalDeliveryResult:
    status: DeliveryStatus
    current_region: str
    owner_region: str
    delivery_type: str
    message_id: str | None = None
    reason: str = ""

    @property
    def delivered(self) -> bool:
        return self.status == DeliveryStatus.DELIVERED

    def as_dict(self) -> dict[str, str]:
        return {
            "currentRegion": self.current_region,
            "ownerRegion": self.owner_region,
            "deliveryType": self.delivery_type,
            "deliveryStatus": self.status.value,
            "deliveryMessageId": self.message_id or "",
            "transportMessageId": self.message_id or "",
            "deliveryReason": self.reason,
        }


class RegionalTransport(Protocol):
    def deliver(
        self,
        request: RegionalDeliveryRequest,
    ) -> RegionalDeliveryResult:
        ...


class SqsRegionalTransport:
    def __init__(
        self,
        *,
        client_factory: Callable[[str], Any],
        queue_names_by_region: Mapping[str, str],
    ) -> None:
        self._client_factory = client_factory
        self._queue_names_by_region = {
            normalize_region(region): str(queue_name or "").strip()
            for region, queue_name in queue_names_by_region.items()
            if normalize_region(region) and str(queue_name or "").strip()
        }
        self._queue_urls_by_region: dict[str, str] = {}
        self._clients_by_region: dict[str, Any] = {}

    def deliver(
        self,
        request: RegionalDeliveryRequest,
    ) -> RegionalDeliveryResult:
        if request.current_region == request.owner_region:
            return RegionalDeliveryResult(
                status=DeliveryStatus.NOOP_LOCAL,
                current_region=request.current_region,
                owner_region=request.owner_region,
                delivery_type=request.delivery_type,
                reason="placement is local",
            )

        queue_name = self._queue_names_by_region.get(
            request.owner_region
        )

        if not queue_name:
            return RegionalDeliveryResult(
                status=DeliveryStatus.UNSUPPORTED_REGION,
                current_region=request.current_region,
                owner_region=request.owner_region,
                delivery_type=request.delivery_type,
                reason="owner region has no configured queue",
            )

        try:
            client = self._clients_by_region.get(
                request.owner_region
            )

            if client is None:
                client = self._client_factory(
                    request.owner_region
                )
                self._clients_by_region[
                    request.owner_region
                ] = client

            queue_url = self._queue_urls_by_region.get(
                request.owner_region
            )

            if not queue_url:
                queue = client.get_queue_url(
                    QueueName=queue_name,
                )
                queue_url = str(
                    queue.get("QueueUrl") or ""
                ).strip()

                if queue_url:
                    self._queue_urls_by_region[
                        request.owner_region
                    ] = queue_url

            if not queue_url:
                return RegionalDeliveryResult(
                    status=DeliveryStatus.DELIVERY_FAILED,
                    current_region=request.current_region,
                    owner_region=request.owner_region,
                    delivery_type=request.delivery_type,
                    reason="SQS did not return a QueueUrl",
                )

            response = client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(
                    request.payload,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ),
            )
            message_id = str(
                response.get("MessageId") or ""
            ).strip()

            if not message_id:
                return RegionalDeliveryResult(
                    status=DeliveryStatus.DELIVERY_FAILED,
                    current_region=request.current_region,
                    owner_region=request.owner_region,
                    delivery_type=request.delivery_type,
                    reason="SQS did not return a MessageId",
                )

            return RegionalDeliveryResult(
                status=DeliveryStatus.DELIVERED,
                current_region=request.current_region,
                owner_region=request.owner_region,
                delivery_type=request.delivery_type,
                message_id=message_id,
                reason="delivered to owner region queue",
            )
        except (BotoCoreError, ClientError, RuntimeError) as error:
            return RegionalDeliveryResult(
                status=DeliveryStatus.DELIVERY_FAILED,
                current_region=request.current_region,
                owner_region=request.owner_region,
                delivery_type=request.delivery_type,
                reason=type(error).__name__,
            )

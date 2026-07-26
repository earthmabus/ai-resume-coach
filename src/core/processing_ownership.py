from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.region_routing import normalize_region


class ProcessingOwnershipStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    LEGACY_LOCAL = "LEGACY_LOCAL"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ProcessingOwnershipDecision:
    status: ProcessingOwnershipStatus
    current_region: str
    message_owner_region: str
    persisted_owner_region: str
    authoritative_owner_region: str
    reason: str

    @property
    def authorized(self) -> bool:
        return self.status in {
            ProcessingOwnershipStatus.AUTHORIZED,
            ProcessingOwnershipStatus.LEGACY_LOCAL,
        }

    def as_dict(self) -> dict[str, str]:
        return {
            "processingOwnershipStatus": self.status.value,
            "currentRegion": self.current_region,
            "messageOwnerRegion": self.message_owner_region,
            "persistedOwnerRegion": self.persisted_owner_region,
            "authoritativeOwnerRegion": self.authoritative_owner_region,
            "processingOwnershipReason": self.reason,
        }


class ProcessingOwnershipError(RuntimeError):
    def __init__(self, decision: ProcessingOwnershipDecision) -> None:
        self.decision = decision
        super().__init__(decision.reason)


def evaluate_processing_ownership(
    *,
    current_region: str | None,
    message_owner_region: str | None,
    persisted_owner_region: str | None = None,
) -> ProcessingOwnershipDecision:
    """Authorize a regional worker to process one logical work item.

    Persisted ownership is authoritative when present. Message ownership must
    agree with it, and the current worker must run in that same region. Legacy
    records/messages without ownership remain locally processable for backward
    compatibility, but ownership is never inferred across regions.
    """

    current = normalize_region(current_region)
    message_owner = normalize_region(message_owner_region)
    persisted_owner = normalize_region(persisted_owner_region)
    authoritative_owner = persisted_owner or message_owner

    if not current:
        return ProcessingOwnershipDecision(
            status=ProcessingOwnershipStatus.REJECTED,
            current_region=current,
            message_owner_region=message_owner,
            persisted_owner_region=persisted_owner,
            authoritative_owner_region=authoritative_owner,
            reason="current worker region is not configured",
        )

    if persisted_owner and message_owner and persisted_owner != message_owner:
        return ProcessingOwnershipDecision(
            status=ProcessingOwnershipStatus.REJECTED,
            current_region=current,
            message_owner_region=message_owner,
            persisted_owner_region=persisted_owner,
            authoritative_owner_region=persisted_owner,
            reason="message owner region conflicts with persisted owner region",
        )

    if authoritative_owner and authoritative_owner != current:
        return ProcessingOwnershipDecision(
            status=ProcessingOwnershipStatus.REJECTED,
            current_region=current,
            message_owner_region=message_owner,
            persisted_owner_region=persisted_owner,
            authoritative_owner_region=authoritative_owner,
            reason="current worker is not the authoritative owner region",
        )

    if authoritative_owner:
        return ProcessingOwnershipDecision(
            status=ProcessingOwnershipStatus.AUTHORIZED,
            current_region=current,
            message_owner_region=message_owner,
            persisted_owner_region=persisted_owner,
            authoritative_owner_region=authoritative_owner,
            reason="current worker matches the authoritative owner region",
        )

    return ProcessingOwnershipDecision(
        status=ProcessingOwnershipStatus.LEGACY_LOCAL,
        current_region=current,
        message_owner_region="",
        persisted_owner_region="",
        authoritative_owner_region=current,
        reason="legacy work without ownership is processed locally",
    )


def require_processing_ownership(**kwargs: str | None) -> ProcessingOwnershipDecision:
    decision = evaluate_processing_ownership(**kwargs)
    if not decision.authorized:
        raise ProcessingOwnershipError(decision)
    return decision

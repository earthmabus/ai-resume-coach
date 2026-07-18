# Request Lifecycle

End-to-end request flow from browser to completed analysis.

## Correlation

Every API command has a `requestId` from API Gateway request context. The
application also accepts a validated `X-Correlation-Id` header for operational
grouping; when the header is absent or invalid, `correlationId` falls back to
`requestId`.

`requestId` is the logical originating command identifier. `correlationId` is
diagnostic grouping metadata and does not replace idempotency keys,
authorization, ownership, or work identifiers.

For newly created idempotent work, the request context supplies both
identifiers to the idempotency record, durable work record, transactional
outbox record, and processing message. A retry or continuation of the same
idempotency key preserves the originally stored `correlationId`; it does not
replace it with the retrying invocation's header.

Legacy records and compatible queue messages without `correlationId` remain
processable. Diagnostics fall back to `requestId` where possible and do not
invent historical correlation values.

## Regional Ownership

Runtime region and owner region are separate concepts.

Runtime region describes where code is currently executing. Owner region
describes which configured region owns a unit of work.

For newly created idempotent commands, the application records `ownerRegion`
with the idempotency reservation. The initial owner is the region handling the
new command. If the same idempotency key is retried or continued later, the
stored `ownerRegion` is preserved and returned with the reservation; a retry
does not replace ownership with the region handling the retry.

Legacy idempotency records without `ownerRegion` remain usable. Ownership
resolution can treat missing ownership as legacy local work when the caller
chooses that compatibility mode.

For development runtime validation only, uploaded-resume analysis creation can
accept `X-Validation-Owner-Region` when all validation controls are enabled:
`ENVIRONMENT=dev`, `ENABLE_SYNTHETIC_PLACEMENT_OVERRIDE=true`, and the
authenticated Cognito principal has the configured validation group claim. The
requested owner must be one of the configured active regions and cannot be the
MRSC witness. This override is recorded on the work item, participates in the
idempotency fingerprint, and is applied only when creating new work.

## Placement Evaluation

Placement evaluation is transport-neutral:

```text
ownership candidate
  -> ownership resolver
  -> routing request
  -> regional routing service
  -> placement result
```

The placement result can describe local, non-local, invalid, or unresolved
placement. It is diagnostic only in the current implementation. HTTP handlers
do not redirect, reject, or forward based on placement.

## API Route Contract

Unauthenticated public API Gateway routes are limited to:

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

Protected product routes require Cognito JWT authorization and include the
current handler routes for profile, target career, uploaded-resume analysis,
text analysis, job matching, tailoring, status retrieval, listing, and delete
operations.

The async resume-analysis workflow depends on:

- `PUT /target-career`
- `POST /resume-upload-url`
- `POST /analyze-uploaded-resume`
- `GET /analysis/{id}`
- `DELETE /analysis/{id}`

Legacy infrastructure route keys `POST /resume-analysis`,
`POST /job-matching`, `GET /job-matching`,
`DELETE /job-matching/{matchId}`, and `POST /resume-tailoring` are obsolete
and are not compatibility aliases for the current handler or frontend route
contract.

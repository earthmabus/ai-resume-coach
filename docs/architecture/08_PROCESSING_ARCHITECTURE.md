# Processing Architecture

Shared processing queue, worker model, retries, DLQ, and rationale.

## Owner Region Metadata

The shared processing queue remains a regional platform capability named
`processing_queue` with a corresponding `processing_dlq`.

New outbox records include `ownerRegion` alongside existing creation metadata
such as `createdRegion` and `createdByRequestId`. The outbox payload also
includes `ownerRegion`, and the outbox publisher preserves it when serializing
the SQS message.

`sourceRegion` remains for compatibility and continues to describe where the
work was submitted. `ownerRegion` describes the region that owns execution of
the work.

Existing outbox records and SQS messages without `ownerRegion` remain
compatible with workers. Missing ownership is handled by the transport-neutral
ownership resolver rather than by changing worker behavior.

## Transport Boundaries

Workers do not yet act on non-local placement. No message is forwarded,
requeued to another region, rejected, or deleted because of placement. Cross
region delivery, failover, and queue-draining behavior are reserved for later
multi-site slices.

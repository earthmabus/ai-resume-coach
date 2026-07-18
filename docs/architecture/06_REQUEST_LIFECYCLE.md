# Request Lifecycle

End-to-end request flow from browser to completed analysis.

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

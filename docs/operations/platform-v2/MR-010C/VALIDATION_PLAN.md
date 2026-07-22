# MR-010C Cross-Region Transport Recovery Validation Plan

## Scenario

Submit through source site while assigning ownership to destination site using the existing development-only synthetic placement override.

## Required assertions

- current region != owner region;
- witness is never selected;
- source publisher attempts the destination queue;
- induced destination transport failure records retryable delivery state and next-attempt metadata;
- business status remains recoverable;
- destination queue is not silently replaced by the local queue;
- transport restoration results in destination processing;
- one logical result exists.

## Failure injection options, in preference order

1. Purpose-built development-only transport denial switch added to the publisher/transport adapter.
2. Temporary IAM deny scoped to the single source publisher role and destination queue.
3. Queue policy denial scoped to the source publisher role.

Do not delete queues, change queue URLs, or disable the destination worker as the primary transport failure mechanism.

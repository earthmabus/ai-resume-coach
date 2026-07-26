# Physical Architecture

> **Status:** Canonical
> **Audience:** Architects, developers, operators
> **Purpose:** Map logical capabilities to deployed AWS topology
> **Owner:** Platform Engineering
> **Related documents:** [Logical architecture](03_LOGICAL_ARCHITECTURE.md), [MVP2 diagrams](../mvp2-disaster-recovery/README.md), [deployment architecture](11_DEPLOYMENT_ARCHITECTURE.md)

## Global and shared plane

Route 53 latency records and health checks publish a global API hostname. The browser application is served through the repository's frontend S3 and CloudFront path. A shared Cognito user pool protects normal application routes. Terraform also models a west-region warm-standby identity recovery foundation; it does not replicate passwords, sessions, issuer identity, or client identity.

DynamoDB provides the shared authoritative state through a multi-Region strongly consistent table. `us-east-1` and `us-west-2` are active replicas. `us-east-2` provides only the MRSC witness responsibility and contains no application API, worker, processing queue, or document bucket.

## Regional application sites

Each active site contains:

- an API Gateway HTTP API and API Lambda;
- an outbox publisher Lambda with a controlled schedule;
- a shared-capability `processing_queue` and `processing_dlq`;
- a worker Lambda and SQS event-source mapping;
- a regional, versioned document bucket;
- application and access logs.

The sites are peers, but durable ownership prevents both workers from treating the same work as locally authorized.

## Resilience overlays

Bidirectional S3 replication covers new object versions and delete markers when enabled; it is asynchronous and does not backfill older objects. CloudWatch dashboards, alarms, artifact buckets, and global/east/west synthetics are feature-gated. Cognito WAF and notification actions remain profile-dependent production controls.

The editable C4 and runtime diagrams are preserved in [the disaster-recovery diagram portfolio](../mvp2-disaster-recovery/README.md).

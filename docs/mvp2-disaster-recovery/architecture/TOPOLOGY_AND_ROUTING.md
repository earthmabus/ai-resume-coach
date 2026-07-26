# Topology and Global Routing

> **Status:** Canonical
> **Audience:** Architects and operators
> **Purpose:** Explain active sites, witness responsibility, and routing behavior
> **Owner:** Platform Engineering
> **Related documents:** [Physical architecture](../../architecture/04_PHYSICAL_ARCHITECTURE.md), [MS-018](../../architecture/platform-resilience/MS-018_GLOBAL_API_ROUTING.md)

The platform has peer application sites in `us-east-1` and `us-west-2`. Each site has a regional API, compute, queue, DLQs, document bucket, and logs. The `us-east-2` region is not an application site; it supplies only the DynamoDB MRSC witness responsibility.

Route 53 latency records publish healthy enabled sites for the global API hostname. Regional readiness health checks inform DNS routing. A Terraform guard rejects disabling both site records. Direct regional endpoints remain available for diagnosis and recovery.

Routing changes affect new ingress only. They do not transfer durable `ownerRegion`, consume a peer queue, move documents, or change the Cognito issuer. This separation is the central availability boundary.

Traceability: [MS-001](../../architecture/decisions/MS-001_MULTI_SITE_TOPOLOGY.md), [MR-007G](../../architecture/platform-v2/MR-007G_GLOBAL_ACTIVE_ACTIVE_API_ROUTING.md), [MS-018](../../architecture/platform-resilience/MS-018_GLOBAL_API_ROUTING.md), and [MR-014 certification](../../certification/MR-014_MULTI_SITE_CERTIFICATION.md).

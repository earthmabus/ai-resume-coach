# Video Walkthrough Talking Points

## Recommended format

Target length: 12–15 minutes. Keep the repository and one architecture diagram visible. Lead with the problem and decisions, not with a file-by-file tour.

## 0:00–1:00 — Opening

- “This is AI Resume Coach, a serverless product and Director-level architecture portfolio project.”
- Explain the product capabilities in one sentence: resume analysis, job matching, tailoring, and interview preparation.
- State the leadership goal: evolve a working single-region application into a resilient, operable, evidence-based multi-site platform.

## 1:00–3:00 — Executive architecture

Show `docs/mvp2-disaster-recovery/01-executive-multi-site-architecture.svg`.

- Two active sites: `us-east-1` and `us-west-2`.
- Route 53 latency routing with health evaluation.
- Shared Cognito identity and DynamoDB MRSC state.
- `us-east-2` witness for the MRSC topology.
- Region-local API, Lambda, SQS, worker, outbox publisher, and S3 document storage.
- Emphasize symmetry and explicit ownership boundaries.

## 3:00–5:00 — Request and workflow correctness

Show `04-runtime-request-and-workflow.svg`.

- Authenticated request enters one active site.
- Deterministic placement establishes the owner region.
- Idempotency protects duplicate submissions.
- Work and outbox state are persisted transactionally.
- Publisher delivers to the owner-region queue.
- Worker claims work and records terminal state.
- Customer reads remain available across regions through shared state.

Key phrase: “The hard part of active-active was not duplicating compute; it was preserving workflow correctness during retries, partial failures, and regional isolation.”

## 5:00–7:00 — Failure and recovery model

Show `05-failure-recovery-and-certification.svg`.

- Explain routing isolation and survivor-region behavior.
- Explain worker interruption, durable backlog, restoration, completion, and queue drain.
- State the non-goals: no automatic owner reassignment, no automatic cross-region queue draining, no invented zero-data-loss claim.
- Explain why those boundaries reduce unsafe recovery behavior.

## 7:00–9:00 — Evidence and delivery discipline

- Show the certification and final acceptance documents.
- Mention automated application and Terraform contract tests.
- Explain approval-gated mutation for chaos and failover exercises.
- Show the tooling taxonomy and how operator commands are grouped by intent.
- Explain how deployment IDs and correlation fields connect source, runtime, and evidence.

## 9:00–11:00 — Production operations and observability

- Open the CloudWatch dashboard definition or screenshot.
- Cover availability: synthetic health, 5XX, latency.
- Cover asynchronous health: queue age/depth, failures, DLQ.
- Cover usage and capacity: API requests, 4XX, Lambda invocations/duration, SQS throughput, DynamoDB consumption.
- Explain that AWS-native metrics show infrastructure activity, while feature adoption and active-user KPIs require bounded application telemetry.
- Mention service objectives, incident response, recurring resilience exercises, backup/restore, and cost reviews.

## 11:00–13:00 — Leadership decisions and tradeoffs

Use three concise examples:

1. Chose correctness and explicit ownership over automatic takeover.
2. Used cost-gated controls to balance portfolio value with recurring cloud spend.
3. Required runtime evidence before calling the architecture complete.

Explain how the work was sliced, reviewed, tested, and documented so implementation could evolve without losing architectural intent.

## 13:00–15:00 — Close

- Summarize what the project demonstrates: product delivery, cloud architecture, distributed systems, resilience, security awareness, operational readiness, and engineering leadership.
- State the next maturity step: real usage baselines, product KPI instrumentation, recurring game days, and production governance.
- End with: “The result is not just a diagram of an active-active system; it is a tested and operable engineering story with explicit decisions, evidence, and boundaries.”

## Optional demo moments

Use only if reliable and rehearsed:

- sign in and submit a resume analysis;
- show processing becoming complete;
- open regional health endpoints;
- show one dashboard view;
- trace one request using correlation identifiers;
- show the certification report summary.

Avoid a live failover or chaos exercise in the primary recording. Use recorded evidence or diagrams unless the exercise has been rehearsed and recovery is guaranteed.

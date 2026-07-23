# Leadership and Architecture Case Study

## Situation

The original application was a functional single-region serverless system. It demonstrated product delivery but did not yet tell a strong story about regional resilience, distributed workflow correctness, recovery, or production operation.

## Leadership challenge

The challenge was not merely to duplicate infrastructure. A credible active-active design had to answer:

- Who owns newly created work?
- How are duplicate submissions handled?
- What remains globally shared versus region-local?
- What happens when routing, a worker, a queue, or a region is impaired?
- How is recovery proven without corrupting durable state?
- How are cost, complexity, and unsupported claims constrained?

## Approach

The work was decomposed into reviewable slices with explicit contracts and validation evidence. Architecture decisions were recorded before implementation details hardened. Tests were expanded alongside each capability. Operational tooling was organized by intent: build, prepare, inspect, validate, and operate.

AI-assisted development was used to accelerate implementation and review, while repository evidence, tests, Terraform plans, runtime validation, and final acceptance remained the source of truth.

## Architecture outcome

The resulting platform uses:

- two symmetric active application sites;
- global health-aware routing;
- Cognito identity;
- a shared DynamoDB MRSC system of record;
- deterministic regional ownership;
- transactional persistence of work and outbox state;
- regional SQS delivery and workers;
- regional document ownership;
- bounded health classification and structured telemetry.

## Critical tradeoffs

### Correctness over automatic takeover

The platform does not silently reassign ownership or drain one region's queue into another. This avoids creating a recovery mechanism that is more dangerous than the outage it is intended to solve.

### Shared state with regional execution

DynamoDB provides shared durable state and cross-region reads, while queues and document storage stay regional. This preserves operational boundaries and makes failure behavior understandable.

### Cost-gated production controls

Dashboards, alarms, tracing, synthetics, and WAF controls are configurable so the portfolio can demonstrate the design without forcing all recurring costs in every environment.

### Certification over assertion

Routing isolation and worker recovery were executed through approval-gated harnesses with evidence and restoration checks. The architecture is described using what was proven, not what was merely intended.

## Measurable engineering outcomes

- A broad automated test suite covering application, infrastructure contracts, tooling, workflow state, and resilience behavior.
- Repeatable regional deployment and validation tooling.
- Runtime-certified routing isolation in both directions.
- Durable backlog and recovery proof during worker interruption.
- Documentation for architecture, operations, decisions, certification, and lessons learned.

## What I would do with a larger organization

With a staffed product organization, I would add clear service ownership, on-call rotation, product analytics, security review, cost allocation, game days, dependency management, and quarterly service reviews. I would also use error budgets and customer-outcome KPIs to guide whether the next investment should be reliability, performance, cost, or product capability.

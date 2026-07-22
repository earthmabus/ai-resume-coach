# MR-010G Recovery Acceptance Review

## Evidence inventory

For each slice record:

- evidence directory;
- Git deployment ID;
- target/source/destination regions;
- failure injected;
- recovery action;
- measured backlog, drain, and completion times;
- final queue/DLQ counts;
- final business and outbox states;
- relevant CloudWatch correlation IDs;
- restoration/no-drift proof.

## Architecture questions

- Which failures recover automatically?
- Which require an operator?
- What is the unit of regional isolation?
- What state remains durable at each failure boundary?
- How are ownership and transport distinguished?
- What stops duplicate processing?
- What happens when the destination region is unavailable?
- What happens when both active regions are unavailable?
- What must never run in the witness region?

## Exit decision

Choose one:

- ACCEPTED — application-level multi-site completion proven;
- ACCEPTED WITH COST-GATED CONTROLS — core active-active proven, global routing/monitoring not permanently enabled;
- NOT ACCEPTED — list blocking failures and required remediation.

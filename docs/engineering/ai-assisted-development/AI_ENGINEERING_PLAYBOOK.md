# AI Engineering Playbook

## Purpose

This playbook describes the AI-assisted engineering lifecycle used in this
repository. It captures what has worked during the multi-site active-active
work without turning that history into a heavyweight process.

Use this playbook for bounded engineering changes where architecture,
operations, compatibility, or long-term maintenance risk matters. Simple,
low-risk fixes can remain lightweight when the repository authority is clear.

## Repository Authority

AI agents and human reviewers must prefer authority in this order:

1. Repository instructions, including `AGENTS.md`.
2. Accepted architecture decisions.
3. Active plans and accepted specifications.
4. Implementation and tests.
5. Agent prompts.
6. Assumptions.

A prompt must not silently override accepted repository decisions. If a prompt
and the repository conflict, the agent must report the conflict and use the
smallest interpretation compatible with repository authority.

## Lifecycle

### 1. Architecture Intent

Purpose: define the architectural direction and the problem being solved.

Entry criteria:

- The need is clear enough to discuss tradeoffs.
- Relevant repository authority has been read.
- Known constraints and non-goals can be stated.

Exit criteria:

- The intended boundary is clear.
- Major conflicts or ambiguities are identified.
- The work can be expressed as a bounded slice or deferred.

### 2. Engineering Design Specification

Purpose: provide the authoritative implementation specification for one bounded
slice.

An EDS defines outcomes and boundaries rather than prescribing every line of
code. It should include the problem statement, repository authority, objective,
constraints, requirements, non-goals, compatibility expectations, validation,
deliverables, and success criteria.

Use an EDS when a change affects architecture, persistence, infrastructure,
security, cross-region behavior, operational semantics, public contracts, or
shared abstractions. A lightweight task is enough for localized fixes,
documentation polish, and clearly scoped maintenance.

Exit criteria:

- The implementation agent can identify what is in scope and out of scope.
- Compatibility expectations are explicit.
- Validation expectations are known.

### 3. AI Implementation

Purpose: implement the accepted specification in the repository.

The implementation agent reads repository authority, inspects the current code,
uses existing abstractions, keeps changes narrow, updates tests and durable
docs, and reports deviations.

Exit criteria:

- The requested slice is implemented.
- Scope did not expand into adjacent roadmap work.
- Focused and full validation have run or any blockers are reported.
- Documentation and decisions are updated when behavior or architecture changed.

### 4. Architectural Readiness Review

Purpose: evaluate whether the design is cohesive enough before it becomes
harder to change.

An ARR reviews layering, responsibility boundaries, coupling, object model,
terminology, extensibility, repository consistency, and architecture debt. It is
not a general style review.

Possible decisions:

- `APPROVED`
- `APPROVED WITH MINOR REFINEMENTS`
- `NOT READY`

ARR findings may produce behavior-preserving refinements before the next
capability is built.

### 5. Operational Readiness Review

Purpose: evaluate production behavior when operational boundaries change.

Use an ORR when a change introduces or materially changes a network boundary,
AWS service use, asynchronous processing, cross-region behavior, persistence,
security boundary, failure semantics, recovery semantics, or
production-critical dependency.

An ORR reviews failure behavior, durability, idempotency, duplicate-delivery
semantics, IAM, configuration, observability, metrics, alarms, performance,
cost, runbook readiness, security, and operational simplicity.

Possible decisions:

- `OPERATIONALLY APPROVED`
- `OPERATIONALLY APPROVED WITH MINOR REFINEMENTS`
- `NOT OPERATIONALLY READY`

### 6. Human Review and Decision

Purpose: keep accountability with the human engineering owner.

The human engineering owner owns product and architecture intent, approves or
rejects specifications, evaluates tradeoffs, reviews AI output, accepts or
rejects readiness decisions, authorizes merge, and remains accountable for the
system.

AI output is evidence and recommendation, not final authority.

### 7. Validation

Purpose: prove the changed repository still satisfies its executable contracts.

Validation is part of implementation, not a follow-up activity. Agents should
run focused tests first, then the full repository workflow described in
[Validation Contract](../VALIDATION_CONTRACT.md). Report exact commands and
results. Never weaken tests to create a passing result. Rerun relevant
validation after the final source change.

### 8. Architecture and Repository Updates

Purpose: make durable knowledge available to the next engineer or agent.

Update architecture docs, runbooks, roadmap notes, and decision records when
behavior, contracts, boundaries, or operational assumptions change. Do not
duplicate material that already exists; link to authoritative documents.

### 9. Merge

Implementation completion does not automatically authorize merge. A normal
merge decision requires:

- accepted specification satisfied
- required readiness review completed
- no unresolved blocking findings
- validation passed
- documentation updated
- architecture decisions recorded when appropriate
- human engineering owner approval

Minor refinements are behavior-preserving improvements that reduce ambiguity,
coupling, risk, or operational burden. Blocking findings mean the slice is not
ready because correctness, architecture, compatibility, security, or production
operation is materially unclear or unsafe.

## Role Separation

### Architecture Partner

- Explores architectural options.
- Challenges assumptions.
- Helps formulate bounded specifications.
- Independently evaluates results.

### Implementation Agent

- Reads repository authority.
- Implements the accepted specification.
- Validates the work.
- Reports deviations, ambiguities, and findings.

### Review Agent

- Assumes another engineer performed the implementation.
- Challenges abstractions and operational assumptions.
- Does not merely defend prior decisions.
- Makes only justified, behavior-preserving refinements unless a correctness
  issue requires more.

### Human Engineering Owner

- Owns product and architectural intent.
- Approves specifications.
- Evaluates tradeoffs.
- Reviews AI output.
- Accepts or rejects readiness decisions.
- Authorizes merge.
- Remains accountable for the system.

## Challenge Every Abstraction

Simplicity is an architectural and operational requirement.

- Assume every abstraction must justify its existence.
- Do not generalize for hypothetical futures.
- Delete rather than add when behavior remains identical.
- Prefer explicit, narrow contracts.
- Optimize for current accepted requirements.
- Avoid frameworks when one implementation exists.
- Avoid speculative extension points.

Example: MR-009A2 kept ownership and placement separate, but did not add a
policy engine. MR-009A3 used the transactional outbox as the shared transport
boundary instead of adding transport calls to every feature.

## Five-Year Ownership Test

Before accepting a design, ask:

- Would I willingly support this for five years?
- Would a future engineer understand the boundaries?
- Could I diagnose it during an incident?
- Are failures predictable?
- Is state recoverable?
- Are names accurate?
- Is this the smallest design that satisfies the accepted need?

This test should favor clarity, diagnosability, and durable decisions. It must
not justify speculative overengineering.

## Scope Discipline

Specifications and reviews prevent scope drift. An agent must not introduce:

- adjacent roadmap capabilities
- speculative frameworks
- generalized registries
- retry or failover behavior outside the accepted slice
- unrelated refactoring
- new infrastructure without justification
- user-visible behavior not included in the specification

When a useful idea is discovered outside scope, record it as a risk, debt item,
or later recommendation. Do not implement it silently.

Example: MR-009A3 introduced one cross-region SQS delivery attempt, but did not
add failover, transport retry, replay, or health-based routing.

## Validation Discipline

Use focused validation while working and full validation before completion.
Distinguish a brittle test from a product defect, but do not weaken meaningful
tests to get green results.

The MR-009A3 and ORR-001 flow is the model: focused transport and outbox tests,
full Python tests, Terraform formatting and validation, focused Terraform tests,
and the platform foundation validation script were run after the final changes.

## Decision and Record Discipline

Completed records should use simple names when preserved as standalone
documents:

- `EDS-001`
- `ARR-001`
- `ORR-001`
- `RDR-001`

Do not store every prompt transcript. Prefer the lightest durable record:
accepted architecture decisions, updated architecture docs, runbooks,
pull-request descriptions, commit history, and review decision records when a
review outcome itself needs to remain searchable.

## Prompt and Template Maintenance

Templates are repository artifacts and should be maintained like code.

- Review template changes through normal pull-request practice.
- Update templates when lessons are proven by repeated work.
- Do not add process rules based on one speculative concern.
- Preserve the distinction between templates and completed records.
- Keep process changes lightweight.

## Evidence-Based Examples

- Work ownership depends on configured topology and persisted metadata, not on
  transport behavior.
- Placement uses neutral terms such as local and non-local instead of implying
  forwarding.
- Cross-region delivery starts at the transactional outbox boundary because it
  is the shared asynchronous contract.
- IAM was narrowed when review showed `GetQueueUrl` could be scoped to queue
  ARNs.
- Queue URL resolution was cached after operational review showed per-message
  discovery added cost and failure exposure without adding correctness.
- At-least-once delivery was documented because the outbox remains the durable
  recovery boundary and distributed transactions were not introduced.

## Anti-Patterns

- Asking AI to build the next thing without boundaries.
- Treating generated code as automatically correct.
- Allowing implementation prompts to override accepted architecture.
- Combining architecture, implementation, and operations into one unreviewed
  step for high-risk work.
- Accepting passing tests as proof of sound architecture.
- Inventing abstractions for hypothetical futures.
- Using AI reviews that merely validate prior AI choices.
- Merging before documentation and decisions are updated.
- Removing meaningful tests to achieve green validation.

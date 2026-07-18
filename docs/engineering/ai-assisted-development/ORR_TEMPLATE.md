# Operational Readiness Review Template

## Purpose

Use an Operational Readiness Review to decide whether a completed change is
safe, observable, supportable, and appropriately simple for production use.

## When To Use

Use this template when a change introduces or materially changes:

- a network boundary
- an AWS service or managed dependency
- asynchronous processing
- cross-region behavior
- persistence behavior
- security boundaries
- failure or recovery semantics
- production-critical operational dependencies

## Title

`ORR-___ - <subject>`

## Repository Authority Reviewed

List instructions, decisions, specifications, runbooks, source files, tests,
Terraform, IAM, logging, metrics, and validation contracts reviewed.

## Operational Architecture Assessment

Describe the runtime path and operational boundary under review.

## Failure Behavior

Review expected behavior under service errors, timeouts, invalid
configuration, permission failures, dependency degradation, process crashes,
and regional degradation.

## Durability and Recovery

Explain where durable state lives and how failed work remains recoverable.

## Idempotency and Duplicate Semantics

Identify duplicate-delivery or repeated-execution windows and the contracts
that make them safe.

## IAM and Security

Assess least privilege, resource scoping, account and region assumptions,
encryption, sensitive data handling, and whether untrusted input can redirect
work.

## Configuration

Assess required configuration, validation, defaults, safety, and deployment
portability.

## Observability

Confirm operators can answer what happened, where it happened, why it failed,
and what will happen next without logging sensitive payloads.

## Metrics and Alarms

List existing signals, gaps required before merge, and later hardening
recommendations.

## Performance and Cost

Assess additional runtime calls, latency, throughput effects, and cost.

## Runbook Readiness

Confirm operators have enough documented guidance to investigate and recover
within the current capability.

## Operational Simplicity

Challenge every API call, permission, configuration value, log field, and
abstraction. Remove or simplify anything not needed for correctness or
operability.

## Required Changes Before Merge

List required refinements and whether they were completed.

## Recommended Later Improvements

List useful operational hardening that is outside the current scope.

## Validation

List focused and full validation run after any final change.

## Decision

Choose one:

- `OPERATIONALLY APPROVED`
- `OPERATIONALLY APPROVED WITH MINOR REFINEMENTS`
- `NOT OPERATIONALLY READY`

Explain the decision and any remaining operational risk.

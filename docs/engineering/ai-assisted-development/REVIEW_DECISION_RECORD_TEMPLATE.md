# Review Decision Record Template

## Purpose

Use a Review Decision Record when a readiness review reaches a decision that
should remain durable but does not require a full architecture decision record.

Prefer existing architecture decisions, runbooks, pull requests, and commit
history when they already preserve the knowledge. Do not create duplicate
records.

## When To Use

Use this template when a completed ARR, ORR, or similar review produces a
decision, constraint, accepted risk, or follow-up that future engineers and AI
agents must be able to find.

## Title

`RDR-___ - <review decision>`

## Status

`Accepted`, `Superseded`, or `Rejected`

## Related Work

List related EDS, ARR, ORR, architecture decisions, pull requests, commits, or
docs.

## Decision

State the review decision in one or two paragraphs.

## Rationale

Explain why this decision was made, including the evidence reviewed.

## Consequences

List the operational, architectural, compatibility, or maintenance impact.

## Accepted Risk

List risks explicitly accepted by the human engineering owner.

## Follow-Up

List later work that should be tracked elsewhere. Do not turn this record into
a backlog.

## Validation Evidence

Summarize validation commands and results that supported the decision.

## Human Decision

Record who accepted or rejected the decision and when, if the repository's
normal review process captures that information.

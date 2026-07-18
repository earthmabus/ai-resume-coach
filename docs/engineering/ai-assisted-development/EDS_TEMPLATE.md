# Engineering Design Specification Template

## Purpose

Use an Engineering Design Specification when a bounded slice needs explicit
architecture, compatibility, validation, and scope control before
implementation.

## When To Use

Use this template for changes involving shared architecture, persistence,
infrastructure, security, operational behavior, public contracts, cross-region
behavior, or broad refactoring risk.

Use a lightweight task instead when the change is local, low-risk, and already
governed by existing repository authority.

## Title

`EDS-___ - <slice name>`

## Problem Statement

Describe the problem or gap. Include why it matters now.

## Repository Authority

List the repository instructions, decisions, docs, tests, source areas, and
infrastructure contracts that must be reviewed before implementation.

## Architectural Objective

State the capability or design outcome this slice must establish.

## Current Behavior

Summarize the relevant existing behavior and contracts.

## Requirements

List required outcomes. Prefer observable behavior and contracts over
line-by-line implementation direction.

## Constraints

List compatibility, architecture, security, operational, cost, and repository
constraints.

## Non-Goals

List adjacent capabilities that must not be implemented in this slice.

## Compatibility Expectations

Describe what must remain backward compatible, including APIs, messages,
persistence, infrastructure, health behavior, and user-visible behavior.

## Documentation Expectations

List docs, runbooks, or decision records that should be updated if behavior or
architecture changes.

## Validation Expectations

List focused tests and full validation commands expected for this slice. Link
to the repository [Validation Contract](../VALIDATION_CONTRACT.md) when
applicable.

## Deliverables

Define the expected completion report sections.

## Success Criteria

State the conditions required to consider implementation complete.

## Open Questions

List unresolved questions. A blocking question should be resolved before
implementation starts.

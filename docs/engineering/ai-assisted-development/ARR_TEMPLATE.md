# Architectural Readiness Review Template

## Purpose

Use an Architectural Readiness Review to decide whether a completed
implementation is architecturally ready before dependent work makes it harder
to change.

The ARR is not a general style review.

## When To Use

Use this template after implementation of a slice that changes layering,
shared abstractions, architecture boundaries, terminology, persistence shape,
or future extensibility.

## Title

`ARR-___ - <subject>`

## Repository Authority Reviewed

List instructions, decisions, specifications, docs, source files, tests, and
infrastructure contracts reviewed.

## Implementation Reviewed

Summarize the implemented slice and the files or contracts reviewed.

## Layering Assessment

Evaluate whether dependencies flow in the intended direction. Identify any
layer that depends upward or knows too much.

## Responsibility Assessment

Evaluate whether each concept owns one clear responsibility.

## Coupling Assessment

Identify coupling between domain, placement, transport, storage, handlers, or
other layers.

## Object Model Assessment

Review value objects, state machines, service objects, and abstractions.
Identify objects that should be removed, split, merged, or renamed.

## Terminology Assessment

Confirm terms have one meaning and do not imply capabilities that do not exist.

## Extensibility Assessment

State whether the next known slice can be added without redesign.

## Repository Consistency Assessment

Compare implementation, tests, docs, roadmap, and decision records.

## Architecture Debt

List only debt that materially affects architecture, coupling, contracts, or
future safe change.

## Required Refactorings

List behavior-preserving changes required before approval.

## Changes Actually Made

If review produced refinements, summarize them.

## Validation

List focused and full validation run after any final change.

## Decision

Choose one:

- `APPROVED`
- `APPROVED WITH MINOR REFINEMENTS`
- `NOT READY`

Explain the decision and any remaining risk.

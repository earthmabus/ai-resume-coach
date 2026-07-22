# MR-016 — Multi-Site Operations and Architecture

## Purpose

Make the certified multi-site implementation understandable, operable, and maintainable after the implementation program closes.

## Changes

- Replace the historical MR-007 target description with the implemented Platform V2 architecture.
- Record the final decisions and implementation pivots.
- Consolidate normal checks, isolation, restoration, worker recovery, certification, and emergency cleanup into one operator runbook.
- Publish final architecture, request-processing, and recovery posters.
- Record final architecture and operational acceptance.

## Acceptance criteria

- Architecture documentation matches `us-east-1`, `us-west-2`, and the `us-east-2` witness design.
- The documented transport is transactional outbox to owner-region SQS.
- Routing isolation is distinguished from compute shutdown and ownership reassignment.
- Every mutating certification action has an explicit restoration path.
- The synthetic placement override is identified as validation-only.
- The final acceptance record distinguishes certified multi-site capability from deferred production-hardening controls.

## Outcome

Multi-site is maintainable, operator-ready, and accurately represented.

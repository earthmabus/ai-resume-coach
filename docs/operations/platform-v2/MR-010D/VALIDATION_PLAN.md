# MR-010D Regional Continuity and Routing Validation Plan

## Phase 1 — Regional continuity, mandatory

- authenticate once against shared Cognito;
- execute a complete deterministic workflow through east;
- read resulting shared state through west;
- execute a complete deterministic workflow through west;
- read resulting shared state through east;
- prove deployment IDs and ownership are correctly reported.

## Phase 2 — Global routing, cost-gated

Only run when global API routing, certificates, hosted zone, and health checks are explicitly approved.

- confirm both sites route-enabled;
- capture DNS resolution and global health baseline;
- isolate one site using supported Terraform routing controls;
- verify the global endpoint reaches the surviving site;
- restore the isolated site;
- capture no-drift and both-site readiness.

The script must reject any attempted `{east=false,west=false}` state before planning.

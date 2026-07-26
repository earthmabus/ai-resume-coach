# MS-017 — Baseline Assessment

## Purpose

Provide one lightweight, repeatable answer to this question:

> Is the deployed platform ready to continue through loss of `us-east-1`?

## Command

```bash
./tools/resilience/platform_readiness.sh
```

The script reads Terraform outputs only. It does not deploy, change routing, or mutate AWS resources.

For machine-readable output:

```bash
./tools/resilience/platform_readiness.sh --json --report /tmp/platform-readiness.json
```

## Readiness model

The 100-point score intentionally stays small:

| Capability | Weight |
|---|---:|
| Two active application sites | 20 |
| DynamoDB MRSC topology | 25 |
| Route 53 latency routing | 20 |
| Route 53 health checks | 15 |
| Cognito multi-Region identity | 10 |
| Cross-Region document continuity | 10 |

A score below 100 means the platform must not be described as surviving a complete `us-east-1` outage.

## Expected current baseline

Based on the existing Terraform contract, the likely score before the next slices is **45/100**:

- Regional application sites: ready
- DynamoDB MRSC: ready
- Route 53 latency routing: blocked until enabled
- Route 53 health checks: blocked until enabled
- Cognito replication: not yet represented
- Document replication: not yet represented

The command evaluates the real Terraform outputs and remains authoritative over this expected baseline.

## Next slice

**MS-018 — Activate Route 53 latency routing and health checks.**

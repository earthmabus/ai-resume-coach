# CI/CD and Release Model

## Principles

Build once, deploy identical artifacts to both Regions, validate before apply, prevent concurrent applies, and smoke-test both sites.

## Stages

```text
Checkout → Compile → Unit tests → Build isolated packages → Build PDF layer → Terraform fmt/init/validate/test/plan → Apply → East smoke tests → West smoke tests → Frontend smoke test
```

The same API, worker, publisher, and layer artifacts are supplied to both regional modules. Code-hash differences are drift unless a controlled phased rollout is explicitly underway.

`DEPLOYMENT_ID` is the Git commit SHA and should be identical in both sites for a normal release.

If east succeeds and west fails, preserve east, keep frontend traffic on east, diagnose west, and reapply. Symmetry is the desired end state, not a reason to destroy a healthy site during incident response.

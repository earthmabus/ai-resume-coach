# MR-014 Controlled Chaos Runbook

Start read-only:

```bash
./tools/multi_site/mr014_chaos_validation.sh catalog
./tools/multi_site/mr014_chaos_validation.sh preflight
```

Authorized execution requires the environment documented by the delegated MR-010 action plus:

```bash
export EXECUTE_CHAOS=YES
export CONFIRM_MUTATION=YES
export CHAOS_SCENARIO=east-isolation
./tools/multi_site/mr014_chaos_validation.sh run
```

Immediately execute the corresponding restore action using `mr010_failover_recovery.sh`, verify MR-012 readiness, and record the outcome in a results JSON. Evaluate it with:

```bash
export MR014_RESULTS_FILE="$PWD/evidence/mr014-results.json"
./tools/multi_site/mr014_chaos_validation.sh evaluate
```

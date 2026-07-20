# MR-009D4 Replacement Package

Copy the files in this package over the repository root, preserving paths.

## Included changes

- `tools/multi_site/mr009d4_runtime_validation.sh`
  - bidirectional Route 53 routing isolation;
  - global routing convergence measurement;
  - authenticated survivor-region writes and reads;
  - automatic safety restoration;
  - timestamped evidence collection.
- `tools/multi_site/inspect_jwt_claims.py`
  - ID-token validation;
  - expiration and minimum remaining-lifetime validation;
  - safe claim summary without token disclosure.
- `tests/test_mr009d4_runtime_tools.py`
  - JWT lifetime regression tests;
  - isolation/restoration safety-contract tests;
  - survivor-flow assertions.
- MR-009D4 validation plan and expanded isolation runbook.

## Validate after extraction

```bash
python -m compileall src tests tools
pytest -q tests

terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra test

bash -n tools/multi_site/mr009d4_runtime_validation.sh
./tools/validate_platform_v2_foundation.sh
```

## Read-only preflight

```bash
./tools/multi_site/mr009d4_runtime_validation.sh
```

The preflight does not change routing unless both `EXECUTE_FAILOVER=YES` and `CONFIRM_MUTATION=YES` are set.

## Authorized runtime execution

```bash
export AWS_PROFILE=<profile>
export TFVARS_FILE="$PWD/infra/<deployment>.tfvars"
export AUTH_TOKEN='<fresh Cognito ID token>'
export SYNTHETIC_PDF="$PWD/<synthetic-file>.pdf"
export EXECUTE_FAILOVER=YES
export CONFIRM_MUTATION=YES

./tools/multi_site/mr009d4_runtime_validation.sh
echo "MR-009D4 exit code: $?"
```

Review the complete plan before allowing each apply. The harness restores both routing records after each scenario and also attempts restoration from its exit trap.

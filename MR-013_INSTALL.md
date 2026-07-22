# MR-013 Overlay Installation

Overlay this package at the repository root:

```bash
unzip -o ~/Downloads/ai-resume-coach-mr013-overlay.zip \
  -d ~/Projects/ai-resume-coach

cd ~/Projects/ai-resume-coach
```

Validate locally:

```bash
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
python -m compileall src tests tools
pytest -q tests
bash -n tools/multi_site/mr013_workflow_state_validation.sh
```

Generate MR-013 evidence:

```bash
./tools/multi_site/mr013_workflow_state_validation.sh
```

Expected result:

```text
MR-013 workflow-state contract: PASS
evidence/mr013-<timestamp>
```

This validator is non-mutating. It evaluates the application transition contract and writes local evidence only.

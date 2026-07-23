# MR-013 Overlay Installation

> **Taxonomy note:** This archived guide has been normalized to the repository's
> current tooling taxonomy. The underlying MR remains historical, but all commands
> below use supported canonical paths.

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
bash -n tools/validate/workflow_state.sh
```

Generate MR-013 evidence:

```bash
./tools/validate/workflow_state.sh
```

Expected result:

```text
MR-013 workflow-state contract: PASS
evidence/mr013-<timestamp>
```

This validator is non-mutating. It evaluates the application transition contract and writes local evidence only.

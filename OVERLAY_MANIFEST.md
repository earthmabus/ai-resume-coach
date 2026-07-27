# Resume Analysis Cache-Version Contract Fix

Updates the two full-suite contract tests to match the intentionally deployed
Resume Analysis asset versions:

- `styles.css?v=31`
- `app.js?v=26`

## Full replacement files

- `tests/tooling/test_resume_analysis_history_controls_panel_contract.py`
- `tests/tooling/test_resume_analysis_target_career_ux_contract.py`

## Apply

```bash
unzip -o ~/Downloads/resume-analysis-cache-version-contract-fix-overlay.zip
```

## Validate

```bash
python -m pytest -q \
  tests/tooling/test_resume_analysis_history_controls_panel_contract.py \
  tests/tooling/test_resume_analysis_target_career_ux_contract.py

python -m pytest -q
```

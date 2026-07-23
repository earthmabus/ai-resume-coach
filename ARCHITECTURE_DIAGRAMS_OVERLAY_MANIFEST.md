# Architecture Diagram Portfolio Overlay Manifest

## Purpose

Replace the earlier three-diagram disaster-recovery poster set with a final seven-diagram portfolio aligned to the implemented and MR-014-certified Platform V2 architecture.

## Files

- `README.md` — adds a direct link to the architecture diagram portfolio.
- `docs/mvp2-disaster-recovery/README.md` — diagram catalog and architectural basis.
- `docs/mvp2-disaster-recovery/01-executive-multi-site-architecture.{dot,svg,png}`
- `docs/mvp2-disaster-recovery/02-c4-context.{dot,svg,png}`
- `docs/mvp2-disaster-recovery/03-c4-container.{dot,svg,png}`
- `docs/mvp2-disaster-recovery/04-runtime-request-and-workflow.{dot,svg,png}`
- `docs/mvp2-disaster-recovery/05-failure-recovery-and-certification.{dot,svg,png}`
- `docs/mvp2-disaster-recovery/06-data-ownership-and-consistency.{dot,svg,png}`
- `docs/mvp2-disaster-recovery/07-architecture-evolution-timeline.{dot,svg,png}`

## Notes

The overlay does not delete the original `01-multi-site-architecture`, `02-request-processing-flow`, or `03-failure-recovery` files. They can be removed later after visual review, or retained as historical versions.

## Validation

```bash
unzip -o ai-resume-coach-architecture-diagrams-overlay.zip
git diff --check
python -m compileall src tools tests
python -m pytest -q
```

# Repository Structure Cleanup Overlay

This overlay:

- merges active onboarding guidance into `README.md` and removes stale `INSTALL.md`/`README.txt`;
- adds the authoritative repository-structure document;
- retains the tooling taxonomy under architecture;
- replaces milestone-named executable files with capability-based names;
- adds one discoverable `run.sh` dispatcher per executable tooling category;
- moves the replay example into `tools/operations/` and removes the top-level `scripts/` directory;
- groups repository/tooling tests under `tests/tooling/`;
- updates current documentation and tests to canonical paths;
- makes context-ZIP creation repository-location independent.

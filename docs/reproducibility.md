# Reproducibility boundaries

The delivered reviewer path reproduces software operations on pinned artifacts. It validates an existing memory, recomputes partial onboarding and exercises a scripted assessment on a separate original fixture. It does not reproduce the published computational analysis or reconstruct original evidence collection.

Use Python 3.12.12 and uv 0.9.17. For release/CI checks use:

```bash
uv sync --locked
uv run --locked pytest
uv run --locked vclogic demo
uv run --locked vclogic demo --offline
uv run --locked vclogic verify
```

Git commits and dependency versions solve different problems: all five source pins are in `manifests/components.lock.json`; selected example bytes are bound by `manifests/reviewer-artifacts.json`; existing component locks constrain package resolution. Preserve all three, the suite revision and runtime report. Do not regenerate component locks to accommodate drift.

First setup needs repository/package access, Python and build artifacts. Offline operation requires the exact checkouts and installed environments already present; lockfiles alone are insufficient for an offline installation. The default core container preinstalls these at build time and runs with networking disabled. Native `--offline` prevents suite fetching/install downloads; it is not an operating-system network sandbox. See [Docker](docker.md) for the enforced network boundary.

Operational timestamps, run IDs, timings and SQLite bytes need not repeat byte for byte. Verify input/config hashes, native artifact validity, investigation/decision hash binding and the expected fixture behavior. Record platform and tool versions for comparisons; no cross-platform certification or bitwise container-build guarantee is implied.

A publication reproduction lane remains unavailable. It requires an immutable coherent archive with rights/access metadata and checksums; exact evidence and temporal/admission policy; memory/bundle/index versions; compatible embedding model revisions; contract, taxonomy, prompts and configs; real frozen investigation and decision outputs; independently reviewed labels, splits and evaluation commands. Rationale measures and investment-decision measures must remain separate. Machine-extracted decisions are not human ground truth.

Fresh online inference may change with provider behavior even when configuration is pinned. Revisiting dynamic public sources is another experiment with its own coverage, identity-review and rights constraints. Neither activity substitutes for preserving the actual outputs used in an analysis. The historical [audit](component-audit.md) records further compatibility risks and missing archived assets.

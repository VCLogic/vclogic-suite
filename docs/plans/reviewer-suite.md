# Reviewer suite implementation plan

Approved design: `docs/component-audit.md`, sections Proposed minimal suite architecture through Proposed validation contract. User authorized implementation after reviewing Phase 1.

Goal: a single uv-managed entry point and CPU-only container that fetch exact component revisions, validates a frozen memory, executes real wiki-only onboarding, runs the existing deterministic assessment example, and reports honest provenance and limitations.

Architecture: standard-library orchestration package; manifest-driven detached Git checkouts; separate component uv environments; existing component CLIs only. Runtime data isolated beneath workspace/runs. Scientific schemas remain component-owned. Default run uses no credentials or model downloads. Live web/assessment explicitly opt in and use existing prepared assets.

## Tasks

- [x] 1. Package and pins: `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `manifests/components.lock.json`, `manifests/reviewer-artifacts.json`. Freeze audited SHAs and existing example file hashes. Test malformed manifest, safe destinations, actual local Git fetching, idempotence and drift refusal.
- [x] 2. Component/environment management: `src/vclogic_suite/components.py`, `runtime.py`, `cli.py`. Provide `components [--fetch]`, `bootstrap [--profile core|web|all] [--offline]`, `doctor`. Fetch exact commits atomically; validate origin/HEAD/clean tree; preserve committed uv locks. Tests first for wrong revisions/origins/dirty sources, offline absence and no secrets in process diagnostics.
- [x] 3. Reviewer orchestration: `demo.py`, `verification.py`; `demo [--offline]`, `verify [--run PATH]`. Copy only manifest-bound data into fresh workspaces. Invoke memory check, onboarding prepare/check/install, assessment index/run/verify via their uv environments. Write per-stage logs and report.json, record separate frozen/mock/partial/unavailable stages. Verify hashes, provenance and native artifact validators; no scientific logic. Tests first for tampering, path escape, expected output structure and no-key environment. End-to-end tests use real pinned components when installed, skip explicitly otherwise.
- [x] 4. Research adapters: `research.py`; `assess --workspace PATH --config PATH --investor SLUG --pitch PATH --allow-paid`; `web --workspace PATH --config PATH`. Fail missing credentials/index readiness before inference; invoke existing rehearsal and web CLI. No new models or scientific formats. Support native local deployment; do not claim a mock is valid for arbitrary pitches.
- [x] 5. Docker and CI: digest-pinned Python/uv base, core default Compose service with no runtime network and writable output mount; optional web image/profile with Node build, explicit prepared assets. Build/run core and compare verification, record constraints. CI unit and real integration smoke on Linux.
- [x] 6. README and guides: reviewer, architecture, reproducibility, full pipeline, Docker and troubleshooting. Explain staged demo limitation, source rights, publication archive gap, separate outcomes and cache/network costs. No invented license/DOI, no component source copies.
- [x] 7. Verification and review: `uv run pytest`, fresh demo, offline repeat, tamper rejection, wheel/CLI, Docker build/run, full-source review. Integrate into original checkout after green tests. Keep audit historical and link new guides.

## Validation commands

`uv sync --locked`; `uv run pytest`; `uv run vclogic demo`; `uv run vclogic demo --offline`; `uv run vclogic verify`; `docker compose config`; `docker compose up --build --abort-on-container-exit --exit-code-from core`.

## Decisions

- Python 3.12.12, uv 0.9.17 initially match audit; no component changes.
- No paid inference or model-weight downloads while developing/testing.
- No release tag or scientific reproduction claim until publication inputs and license/rights decisions are supplied.
- Runtime checkouts are ignored; data hashes, not third-party raw content, tracked by suite.
- Component content and native CLIs may be fetched by network only during setup; `--offline` never fetches.

## Execution record

All implementation tasks completed; see `docs/implementation-verification.md` for commands and evidence. Final review caught and tests fixed editable-dependency verification and native Ollama embedding identity.

Ruling: core Docker shipped; web Docker deferred because no ready publication assets are supplied. Native web launcher/build works as an explicit prepared-workspace adapter; this costs users a local Node build for the optional UI.
Ruling: grounded-only live adapter requires canonical_config_path; other native rehearsal modes use the component CLI, avoiding invented behavior.
Ruling: no license or publication archive invented; NOTICE and explicit unavailable report retain this release boundary.

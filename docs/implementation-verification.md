# Implementation verification

Verified on 2026-10-07 with CPython 3.12.12 and uv 0.9.17 on Linux. This records engineering checks; it is not a publication-results reproduction report.

- `uv sync --locked` and `uv run pytest`: lightweight contract tests pass; real component tests explicitly skip unless `VCLOGIC_INTEGRATION=1` is set.
- `uv run vclogic bootstrap --profile all`: all five exact revisions acquired, locked base environments installed, existing web frontend built. No optional model/AV dependencies or weights installed.
- `VCLOGIC_INTEGRATION=1 uv run pytest`: **17 passed**, including actual memory validation, onboarding prepare/check/install, fake assessment index/run/verify, source/evidence integrity, tampered decision rejection, false-readiness rejection and disabled inherited tracing.
- A separate clean Git clone completed the documented `uv sync --locked`, `uv run vclogic demo`, and `uv run vclogic verify` sequence successfully, without relying on the audit checkouts.
- A built wheel installed into an isolated uv environment and listed all five pinned components using `--root` to locate suite manifests. Runtime data/manifests belong to the suite checkout, not the Python wheel.
- Research preflight rejected both an unindexed investor and a web workspace with no ready investors, without model calls. Provider identity tests use the native adapters with inert injected model/client objects; Ollama normalization/prefix conventions are preserved.
- Core Docker build, network-disabled/read-only execution, and a second verification container passed. See [Docker](docker.md) for measurements and platform limits.
- Ruff checks and formatting pass. No component tracked source was modified. No paid inference, live crawling, model download, scientific refactor, license assignment or release tag was performed.

Independent review found two issues, both fixed with regression tests: web commands now verify the editable assessment dependency before importing it; research readiness uses provider-native embedding identity rather than assuming Sentence Transformers defaults for Ollama. The review found no additional significant core/container issues.

The optional research adapter intentionally supports grounded configurations with a canonical baseline. Other native rehearsal modes remain accessible through the component CLI. A web container is deferred; native web setup/launch is provided, and its production model behavior was not exercised. Publication reproduction remains unavailable until the matching archive, human targets and analysis specification are supplied.

## Staged research CLI and shared environment

The research-stage addition was checked separately on 2026-10-07:

- `uv run pytest`: **31 passed, 2 skipped**. New tests exercise root dotenv
  precedence/restoration, no-key isolation, managed artifact paths, native failure
  propagation, partial bundle readiness, and embedding-extra installation receipts.
- Real `onboard --skip-indexes` against the pinned onboarding component prepared,
  checked and installed the frozen Elizabeth memory into the managed research tree.
- The native collector wizard help ran through the suite subprocess adapter.
- The existing `vclogic test` smoke workflow passed after the changes.
- Ruff, `uv lock --check`, and Git whitespace checks passed. A separate code review
  checked the pinned native command signatures and environment boundary. The
  native restriction against upgrading an installed partial bundle in place is
  explicitly documented in the full workflow guide.

These checks do not claim successful live discovery, paid memory generation,
embedding model downloads, or a new investor's live assessment. Those require
provider authentication, operator review, optional dependencies and native research
configuration. No component source was modified.

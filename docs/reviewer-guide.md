# Reviewer guide

From the suite root, run `uv sync`, `uv run vclogic init`, then `uv run vclogic test`. `uv sync` installs the suite CLI; `init` fetches all five exact Git revisions and installs all component environments and builds the web frontend, with step-based progress reporting. This default requires Node.js/npm as well as uv and Git. Use `--profile core` for only the CPU reviewer dependencies, or `--profile web` for reviewer and web dependencies without the collector environment. All profiles fetch all five repositories; optional AV extras and model weights remain separate. `test` runs only the no-key smoke workflow with component validators and provenance checks, returning a nonzero exit status on failure. It never downloads or installs anything and asks you to run `init` if setup is missing or stale. `verify` revalidates a saved run; `uv run pytest` runs the suite developer tests. Setup downloads Git revisions and Python dependencies. It does not download embedding or generation model weights. A prepared installation supports `uv run vclogic test --offline`; an empty cache does not.

The run report distinguishes these outcomes:

| Stage | What happens | Interpretation |
|---|---|---|
| Frozen memory | Hash-bound Elizabeth Yin memory checked by the real memory validator | Frozen generated content; not freshly generated or independently semantically certified |
| Wiki-only onboarding | Real prepare/check/install with indexing skipped | Recomputed packaging; valid=true, ready_for_assessment=false |
| Existing assessment | Original Elizabeth/Thoras prepared inputs indexed, run and verified by the engine | Mock provider, v1 contract, separate snapshot; rationales and decisions are scripted |
| Publication analysis | No canonical archive or metric inputs supplied | Unavailable; cannot count as reproduced |

The onboarding workspace and assessment workspace are separate by design. Sharing an investor name does not make their memory versions interchangeable. The default run does not collect sources, generate a new memory, extract historical decisions or authorize paid inference.

Open `workspace/latest.json`, then the referenced run’s `report.json` and Markdown summary. Review stage statuses and logs, source revisions, artifact/config hashes, provider and contract, and the paths to native outputs. Follow rationale evidence IDs through recorded retrieval reads to source paths, quotations and hashes. Read coverage/source-policy warnings in the frozen memory; a structural validator does not decide whether evidence is temporally admissible.

Use `uv run vclogic verify --run /absolute/path/to/workspace/runs/<id>` to inspect a particular run. Verification needs its pinned components and installed environments. Preserve the whole run directory: copying only the decision JSON loses context and provenance. Hashes detect changes relative to the recorded inventory; they are not signatures or an independent attestation of research truth.

Rationale reconstruction and decision prediction require distinct human targets and evaluation measures. The demo supplies neither empirical accuracy estimates nor publication metric tables. The fake provider’s probabilities are fixture values, not measured predictions. A successful exit validates software behavior within these boundaries.

For a container run, follow [Docker](docker.md). For real inference and prepared UI assets, follow [the full workflow](full-pipeline.md). Existing component test results and compatibility caveats are preserved in [the historical audit](component-audit.md).

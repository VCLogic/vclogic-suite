# Full research workflow

This is an opt-in research workflow requiring reviewed evidence, coherent native configurations and prepared assets. The default demo covers only the staged software demonstration described in [the reviewer guide](reviewer-guide.md). No live inference or public collection was executed to validate this guide; command contracts were inspected at the pinned revisions in [the audit](component-audit.md).

Fetch all pinned sources, then install the required profile:

```bash
uv run vclogic components --fetch
uv run vclogic bootstrap --profile all
```

Base environments do not install every AV, embedding or research extra, provision model weights, authenticate services, or build every research dataset. Select those requirements explicitly in the owning component. For native commands below, run from the named checkout unless a prepared workspace is specified. Preserve the adjacent sibling layout.

## 1. Collect and review evidence

In `.components/vclogic-vc-trace-collector`, inspect the actual interfaces before supplying identity/source choices:

```bash
uv run --locked vc-trace-collector --help
uv run --locked vc-trace-collector discover --help
uv run --locked vc-trace-collector review --help
uv run --locked vc-trace-collector collect --help
uv run --locked vc-trace-collector export --help
uv run --locked vc-trace-collector verify --help
```

The staged route is discover → human identity/source review → fetch/collect → process → export → verify. Do not auto-confirm those review decisions. Export the entire `outputs/<slug>/` tree, including identity, canonical corpus, processed/raw snapshots and provenance. Portfolio source pages are evidence, not verified holdings.

Public discovery/fetching needs network access. AV can require yt-dlp, ffmpeg, Whisper, gated pyannote access and model weights; these are absent from core. The audit found legacy `full_text`/`text` and `verified_human` admission mismatches at the collector/memory boundary. Choose and document the supported input route without silently rewriting source policy.

## 2. Generate and validate memory

Use the onboarding environment's memory CLI from its checkout for the dependency-light interfaces. Replace paths with absolute locations; preserve the collector investor directory name/identity:

```bash
uv run --locked investor-memory inventory /absolute/export/<slug> --output /absolute/research/inventory.json
uv run --locked investor-memory full-build /absolute/export/<slug> --output /absolute/research/wiki/<slug> --cache-dir /absolute/research/memory-cache
uv run --locked investor-memory check /absolute/research/wiki/<slug>
```

`full-build` invokes authenticated Codex CLI and may consume paid inference. It is not run by suite setup/demo. Output must be new and disjoint from input; keep cache separate. PDF extraction requires the memory `full` extra, whose independent environment is not currently upstream-locked. Resolve that environment explicitly if the evidence requires it.

Retain coverage warnings, input inventory, source reviews, identity resolutions, evidence offsets/citations and generation configuration. Full-build does not enforce a research time cutoff. Establish temporal admissibility and leakage exclusions, and perform semantic review independently of structural validation.

## 3. Prepare a ready onboarding bundle

From the onboarding checkout, prepare a validated wiki after explicitly installing/configuring the embedding runtime and pinned model needed for real indexing:

```bash
uv run --locked investor-onboarding prepare --wiki /absolute/research/wiki/<slug> --output /absolute/research/bundle
uv run --locked investor-onboarding check --bundle /absolute/research/bundle
uv run --locked investor-onboarding install --bundle /absolute/research/bundle --pipeline-workspace /absolute/research/workspace
```

Create the workspace directory before install. Omitting `--skip-indexes` builds semantic indexes and may download weights. Check both validity and `ready_for_assessment`, then verify query embedding compatibility. Index identity includes model/revision, normalization and text prefixes. A frozen index does not supply a query model.

Optional Pitch Show ingestion changes this workflow: `--from-pitch-show` can perform paid two-pass decision extraction. `--collect-only` suppresses that extraction, but live collection still uses HTTP. For a cached no-generation path, supply `--from-pitch-show --pitch-show-cache /absolute/cache --collect-only --skip-indexes`; readiness remains false. Do not pass `--collect-only` to wiki-only preparation. Human review rows create evaluation labels; machine extraction remains a separately labelled ledger.

## 4. Run a chosen assessment contract

Use an assessment-native workspace with reviewed investor registration, taxonomy, wiki/indexes and audited pitch manifests. Copying an arbitrary pitch into a previously hashed package invalidates its contract. Keep evaluation labels outside the inference inputs. Select and preserve the intended native TOML; the newest contract is not automatically the publication method. v4.4 is Phase-1-only.

For an already prepared historical assessment, invoke the assessment environment's existing `vc-clone-graph preflight`, `run` and `verify` with `--config /absolute/path/to/native.toml`, setting the process working directory to the prepared workspace. Native relative paths resolve against that workspace. The executable lives in the assessment checkout's `.venv/bin/` on Linux/macOS. Run preflight before paid work; it does not replace human input review.

For a new pitch, the suite adapter delegates to existing rehearsal start and requires explicit cost authorization:

```bash
uv run vclogic assess --workspace /absolute/research/workspace --config /absolute/research/workspace/configs/rehearsal.toml --investor <slug> --pitch /absolute/research/pitch.txt --allow-paid
```

Configure generation and embedding providers separately if required, export only their selected credential names, and prepare models/indexes first. `--allow-paid` authorizes the adapter's live path; it does not promise a budget or free local execution. Memory generation uses Codex authentication; OpenRouter/OpenAI assessment uses configured API-key names; local Ollama requires its own running service and weights. `.env.example` contains placeholders only.

Preserve investigation and decision JSON separately, their hash binding, retrieval reads, source quotations, native configuration, model identity and usage/provenance receipts. Evaluate rationales against independently reviewed rationales and investment decisions against independent outcomes, retaining abstentions, failures and coverage. A publication archive and exact evaluation specification have not yet been supplied, so no generic evaluation command is claimed to reproduce the paper.

## 5. Optionally launch the UI

Build the existing frontend from the web checkout's `web/frontend` with `npm ci` and `npm run build`. The audit used Node 25.8.2/npm 11.11.1; the component README asks for Node 22.12+. The core container deliberately omits Node; use a compatible local Node installation for the optional web build.

Use a ready prepared workspace and native rehearsal config:

```bash
uv run vclogic bootstrap --profile web
uv run vclogic web --workspace /absolute/research/workspace --config /absolute/research/workspace/configs/rehearsal.toml --allow-paid
```

The UI uses the assessment engine and can make live provider calls when the user starts research actions. The default partial demo bundle does not meet its readiness requirements. HTTP health alone does not validate an investor. Preserve projects, sessions, settings, snapshots, checkpoints and outputs. See [Docker](docker.md) for the core container and why a web container is not included in this release.

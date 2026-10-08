# Full research workflow

This is an opt-in research workflow requiring reviewed evidence, coherent native configurations and prepared assets. The default demo covers only the staged software demonstration described in [the reviewer guide](reviewer-guide.md). No live inference or public collection was executed to validate this guide; command contracts were inspected at the pinned revisions in [the audit](component-audit.md).

## Suite commands and shared credentials

Run everything from the suite root. Copy `.env.example` to `.env` and fill only
credentials required by your chosen providers. All research commands below,
including `assess` and `web`, load this one file and pass settings to native
processes. Shell-exported variables take precedence. Values are literal; there
is no shell execution or `${...}` interpolation. Component-local dotenv loading
is disabled for these subprocesses. No credentials are copied into checkouts or
run reports. No-key `test`, `demo`, and `verify` do not load `.env`.

```bash
uv run vclogic init
uv run vclogic discover --name "Investor Name"
# Use the actual slug printed by discovery in the commands below:
uv run vclogic collect --investor investor-slug
uv run vclogic process --investor investor-slug
uv run vclogic memory --investor investor-slug --allow-paid
uv run vclogic onboard --investor investor-slug
uv run vclogic assess --investor investor-slug --pitch /absolute/path/pitch.txt --allow-paid
uv run vclogic web --investor investor-slug --allow-paid
```

`discover` and `collect` use the collector's interactive wizard, preserving its
identity, source, and budget review. `collect` downloads selected sources;
`process` processes downloaded sources, then exports and verifies the corpus.
`memory` first verifies the collector export, invokes native `full-build`, then
checks the memory. This is the full-export review method described below, not
the legacy curated-source importer. `onboard` prepares, checks and installs the
native bundle. `assess` starts native rehearsal for a new pitch using the
installed investor configurations; `web` uses the same workspace.

Paths are resolved automatically under `workspace/research/`:

| Artifact | Location |
|---|---|
| Collector sources and export | `traces/<investor-slug>/` |
| Generated Investment Memory | `wiki/<investor-slug>/` |
| Memory generation cache | `memory-cache/<investor-slug>/` |
| Onboarding bundle | `bundles/<investor-slug>/` |
| Installed assessment/web workspace | `pipeline/` |

Global `--workspace /absolute/path` before the command relocates this tree.
Existing `assess --workspace ... --config ...` and `web --workspace ... --config ...`
overrides remain available. Existing memories and bundles are not overwritten;
use a new workspace for another version. Native caches and collector state can
be reused when retrying interrupted work. Stage execution stops on the first
nonzero native exit status. Inspect native warnings and human review outcomes,
not merely the final command exit status.

For an already prepared historical pitch package, run native graph stages:

```bash
uv run vclogic pipeline --investor investor-slug --config configs/investors/investor-slug/canonical.toml --allow-paid
```

This delegates to `vc-clone-graph preflight`, `run`, and `verify`. Config paths
resolve inside `workspace/research/pipeline/`. A newly onboarded wiki alone does
not supply a historical pitch package: use `assess --pitch` for a new pitch.
Review the native provider/model/contract configuration before generation;
`.env` supplies credentials, not a new research methodology.

Selected native options can follow `--`; paths in those options should be absolute:

```bash
uv run vclogic process --investor investor-slug -- --transcription-model MODEL
uv run vclogic memory --investor investor-slug --allow-paid -- --model MODEL --workers 3
uv run vclogic onboard --investor investor-slug --allow-paid -- --from-pitch-show --max-episodes 5
```

Suite-managed paths and stage selection cannot be overridden by forwarded flags.
`onboard --skip-indexes` is available for an explicitly partial bundle and reports
`ready_for_assessment=false`; it cannot support live assessment. Treat this as a
terminal partial artifact for that workspace: the native installer never overwrites
an installed bundle, so this command is not an in-place upgrade route. For live
research, install embedding dependencies first and omit `--skip-indexes`. Wiki-only indexing
can download the pinned embedding model. Pitch Show extraction can use paid
inference and requires `--allow-paid`; `--collect-only` avoids extraction but can
still access public websites.

Plain `init` installs all locked component extras needed for the research workflow:
embeddings, personalized assessment, collector browser/YouTube/AV/Whisper/pyannote,
plus PDF extraction from `configs/memory-pdf.lock`. It downloads Chromium and
builds the web frontend. `init --embeddings` remains accepted and is equivalent
with the default all profile. `init --profile core` is the smaller no-model reviewer
installation; add `--embeddings` to core or web when semantic indexing is needed.

Model weights load later according to the selected models. Full initialization
checks ffmpeg, Node/npm, Codex, Agent Reach and mcporter and verifies Chromium can
launch. Missing prerequisites are reported with a nonzero exit, after retaining
successful setup work. It does not run sudo or silently install global system
software. Authenticate Codex/provider services, accept gated model licenses, and
configure external Agent Reach backends before their first use. CUDA drivers and
local provider services remain host-specific. No setup command performs inference.
The commands were validated with mocks and a real frozen-memory partial onboarding
run; no live public-data collection or paid generation was executed as a test.

The sections below document native interfaces and remaining research requirements.

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

The suite research adapter currently requires a grounded rehearsal config with `classification.canonical_config_path` inside the selected workspace. Use the native component CLI for other rehearsal modes.

For a new pitch, the suite adapter delegates to existing rehearsal start and requires explicit cost authorization:

```bash
uv run vclogic assess --workspace /absolute/research/workspace --config /absolute/research/workspace/configs/rehearsal.toml --investor <slug> --pitch /absolute/research/pitch.txt --allow-paid
```

Configure generation and embedding providers separately if required, set their selected credential names in the suite root `.env`, and prepare models/indexes first. `--allow-paid` authorizes the adapter's live path; it does not promise a budget or free local execution. Memory generation uses Codex authentication; OpenRouter/OpenAI assessment uses configured API-key names; local Ollama requires its own running service and weights. `.env.example` contains placeholders only.

Preserve investigation and decision JSON separately, their hash binding, retrieval reads, source quotations, native configuration, model identity and usage/provenance receipts. Evaluate rationales against independently reviewed rationales and investment decisions against independent outcomes, retaining abstentions, failures and coverage. A publication archive and exact evaluation specification have not yet been supplied, so no generic evaluation command is claimed to reproduce the paper.

## 5. Optionally launch the UI

Build the existing frontend from the web checkout's `web/frontend` with `npm ci` and `npm run build`. The audit used Node 25.8.2/npm 11.11.1; the component README asks for Node 22.12+. The core container deliberately omits Node; use a compatible local Node installation for the optional web build.

Use a ready prepared workspace and native rehearsal config:

```bash
uv run vclogic bootstrap --profile web
uv run vclogic web --workspace /absolute/research/workspace --config /absolute/research/workspace/configs/rehearsal.toml --allow-paid
```

The UI uses the assessment engine and can make live provider calls when the user starts research actions. The default partial demo bundle does not meet its readiness requirements. HTTP health alone does not validate an investor. Preserve projects, sessions, settings, snapshots, checkpoints and outputs. See [Docker](docker.md) for the core container and why a web container is not included in this release.

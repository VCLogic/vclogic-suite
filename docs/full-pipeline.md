# Full research workflow

This is an opt-in research workflow requiring reviewed evidence, coherent native configurations and prepared assets. The default demo covers only the staged software demonstration described in [the reviewer guide](reviewer-guide.md). No live inference or public collection was executed to validate this guide; command contracts were inspected at the pinned revisions in [the audit](component-audit.md).

## A new investor, step by step

All commands run from the suite root.

### 0. Set up once

```bash
uv sync
uv run vclogic init          # fetch the five pinned repositories, install everything
uv run vclogic doctor        # every component must say "pinned and clean"
cp .env.example .env         # then fill only the credentials your providers need
```

`init` also moves clean component checkouts to new pins after a suite update.
It refuses to touch a checkout with local changes.

Log in to at least one memory-generation harness: [Codex CLI](https://developers.openai.com/codex/cli/)
or [Claude Code](https://code.claude.com/docs/en/setup). `init` reports it as a
missing prerequisite when neither is on `PATH`. For audio and video sources, set
`HF_TOKEN` in `.env` and accept the gated pyannote models on Hugging Face.

The wizard's Agent Reach/Exa search runs through `mcporter` with an `exa` server.
Behind an HTTP(S) proxy, set `NODE_USE_ENV_PROXY=1` in `.env`, then check it with
`NODE_USE_ENV_PROXY=1 mcporter list`, which should show `exa` as healthy. Otherwise,
pick the default search backend in the wizard. The `agent-reach` executable is optional.

### 1. Two configuration files

| File | Holds | Committed |
|---|---|---|
| `.env` | Secrets: `OPENROUTER_API_KEY`, `HF_TOKEN`, collector endpoints | Never |
| `vclogic.toml` | Settings: `allow_paid`, memory `harness`, extra native options per stage, web port | Yes |

Every research command loads both. Shell-exported variables win over `.env`, and
command-line flags win over `vclogic.toml`. `.env` values are literal (no `${...}`
expansion), and component-local `.env` files are ignored. No-key `test`, `demo`
and `verify` load neither file.

Set `allow_paid = true` in `vclogic.toml` once you accept that memory generation,
Pitch Show extraction and assessments spend money. Otherwise, pass `--allow-paid`
to those commands. To choose the memory harness without being asked, set
`harness = "codex"` or `harness = "claude"`.

### 2. Run the whole investor pipeline

```bash
uv run vclogic run --name "Jane Roe" --allow-paid
```

1. **Collect (interactive).** The collector's guided wizard confirms the identity,
   lets you skip platforms, triage sources, download them, pick voice references,
   then process, export and verify the corpus. This is the only step that needs you.
   Quitting saves progress.
2. **Memory.** The suite verifies the export, then runs `investor-memory full-build`
   with the harness from `vclogic.toml`, then validates the memory.
3. **Onboard.** The suite prepares the bundle with semantic indexes, checks that it
   is valid and `ready_for_assessment`, then installs it into the pipeline workspace.
4. The suite prints the commands for assessment and the web app.

`run` resumes. Rerun it with the slug it printed:

```bash
uv run vclogic run --investor jane-roe --allow-paid
```

A finished collection is not repeated, and an existing memory is revalidated rather
than regenerated. An investor that is already installed is not reinstalled.

The same stages run one at a time:

```bash
uv run vclogic collect --name "Jane Roe"          # or --investor jane-roe to resume
uv run vclogic process --investor jane-roe        # only to re-process/export/verify
uv run vclogic memory  --investor jane-roe --allow-paid
uv run vclogic onboard --investor jane-roe
```

### 3. Assess a pitch

```bash
uv run vclogic assess --investor jane-roe --pitch /abs/path/pitch.txt --company "Acme" --allow-paid
```

The engine builds the investor's assessment: Phase 1 investigates the investor's
rationales, and Phase 2 synthesizes the investment decision. The suite then prints
the assessment and saves it as `workspace/research/assessments/jane-roe/<session>.md`
and `.json`. `--company` is required and repeatable, because the engine excludes
that company's material from retrieval to prevent leakage. The same session can
continue as a rehearsal in the web app.

### 4. Web interface

```bash
uv run vclogic web --allow-paid
```

The command serves every installed investor at `http://localhost:8000` (or the
port set by `[web] port` in `vclogic.toml`). Assessments and rehearsals can also
be started there. Leave it running. An investor onboarded by `vclogic run` or
`vclogic onboard` appears in the list without a restart. For a few seconds after
startup the list can be empty while the catalog validates the installed indexes.

### 5. Agent skill

Claude Code (`/vclogic`) and Codex (`$vclogic`) have a suite skill under
`.agents/skills/vclogic/`. It runs the unattended stages and assessments, and it
asks you to run the interactive collection wizard yourself with `! uv run vclogic collect ...`.

### Paths

Paths are resolved automatically under `workspace/research/`:

| Artifact | Location |
|---|---|
| Collector sources and export | `traces/<investor-slug>/` |
| Generated Investment Memory | `wiki/<investor-slug>/` |
| Memory generation cache | `memory-cache/<investor-slug>/` |
| Onboarding bundle | `bundles/<investor-slug>/` |
| Installed assessment/web workspace | `pipeline/` |
| Pitch assessments | `assessments/<investor-slug>/` |

Global `--workspace /absolute/path` before the command relocates this tree. Existing
memories and bundles are never overwritten; use a new workspace for another version.
Stages stop at the first nonzero native exit. Inspect native warnings and human
review outcomes, not only the final exit status.

Native options can be set per stage in `vclogic.toml` (`[memory] args = [...]`), or
after `--` for a single run. Suite-managed paths cannot be overridden:

```bash
uv run vclogic memory --investor jane-roe --allow-paid -- --harness claude --model sonnet
uv run vclogic onboard --investor jane-roe --allow-paid -- --from-pitch-show --max-episodes 5
```

`onboard --skip-indexes` produces an explicitly partial bundle
(`ready_for_assessment=false`) that cannot support assessment. The native installer
never overwrites an installed bundle.

For an already prepared historical pitch package, `uv run vclogic pipeline --investor
<slug> --config configs/investors/<slug>/canonical.toml --allow-paid` runs native
`vc-clone-graph preflight`, `run` and `verify`.

`init` installs every locked extra: embeddings, personalized assessment, collector
browser/YouTube/AV/Whisper/pyannote, and PDF extraction from `configs/memory-pdf.lock`.
It also installs Chromium and builds the web frontend. `init --profile core` is the
small no-model reviewer install. No setup command performs inference. Model weights
download on first use.

The sections below document native interfaces and remaining research requirements.

## 1. Collect and review evidence

In `.components/vclogic-vc-trace-collector`, inspect the actual interfaces before supplying identity/source choices:

```bash
uv run --locked vc-trace-collector --help
uv run --locked vc-trace-collector review --help
uv run --locked vc-trace-collector collect --help
uv run --locked vc-trace-collector export --help
uv run --locked vc-trace-collector verify --help
```

The collector `wizard` is one guided route: identity → platforms → triage → fetch → voice reference → process → export/verify. Do not auto-confirm its review decisions. Export the entire `outputs/<slug>/` tree, including identity, canonical corpus, processed/raw snapshots and provenance. Portfolio source pages are evidence, not verified holdings.

Public discovery/fetching needs network access. AV can require yt-dlp, ffmpeg, Whisper, gated pyannote access and model weights; these are absent from core. The audit found legacy `full_text`/`text` and `verified_human` admission mismatches at the collector/memory boundary. Choose and document the supported input route without silently rewriting source policy.

## 2. Generate and validate memory

Use the onboarding environment's memory CLI from its checkout for the dependency-light interfaces. Replace paths with absolute locations; preserve the collector investor directory name/identity:

```bash
uv run --locked investor-memory inventory /absolute/export/<slug> --output /absolute/research/inventory.json
uv run --locked investor-memory full-build /absolute/export/<slug> --output /absolute/research/wiki/<slug> --cache-dir /absolute/research/memory-cache
uv run --locked investor-memory check /absolute/research/wiki/<slug>
```

`full-build` invokes the selected authenticated harness (`--harness codex` or `--harness claude`) and may consume paid inference. It is not run by suite setup/demo. Output must be new and disjoint from input; keep cache separate. PDF extraction requires the memory `full` extra, whose independent environment is not currently upstream-locked. Resolve that environment explicitly if the evidence requires it.

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

Configure generation and embedding providers separately if required, set their selected credential names in the suite root `.env`, and prepare models/indexes first. `--allow-paid` authorizes the adapter's live path; it does not promise a budget or free local execution. Memory generation uses the Codex or Claude Code login; OpenRouter/OpenAI assessment uses configured API-key names; local Ollama requires its own running service and weights. `.env.example` contains placeholders only.

Preserve investigation and decision JSON separately, their hash binding, retrieval reads, source quotations, native configuration, model identity and usage/provenance receipts. Evaluate rationales against independently reviewed rationales and investment decisions against independent outcomes, retaining abstentions, failures and coverage. A publication archive and exact evaluation specification have not yet been supplied, so no generic evaluation command is claimed to reproduce the paper.

## 5. Optionally launch the UI

Build the existing frontend from the web checkout's `web/frontend` with `npm ci` and `npm run build`. The audit used Node 25.8.2/npm 11.11.1; the component README asks for Node 22.12+. The core container deliberately omits Node; use a compatible local Node installation for the optional web build.

Use a ready prepared workspace and native rehearsal config:

```bash
uv run vclogic bootstrap --profile web
uv run vclogic web --workspace /absolute/research/workspace --config /absolute/research/workspace/configs/rehearsal.toml --allow-paid
```

The UI uses the assessment engine and can make live provider calls when the user starts research actions. The default partial demo bundle does not meet its readiness requirements. HTTP health alone does not validate an investor. Preserve projects, sessions, settings, snapshots, checkpoints and outputs. See [Docker](docker.md) for the core container and why a web container is not included in this release.

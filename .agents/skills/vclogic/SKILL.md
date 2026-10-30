---
name: vclogic
description: Use when asked to onboard a new venture investor end to end (collect public traces, build the investment memory, onboard, install for the web app), resume that work, assess a founder pitch against an onboarded investor, or start the VCLogic web interface from the vclogic-suite checkout.
---

# VCLogic suite

Drive the whole VCLogic workflow through the suite CLI. The suite pins the five
component repositories, passes the root `.env` (secrets) and `vclogic.toml`
(settings) to every stage, and resolves all handoff paths under
`workspace/research/`. Never call component CLIs directly or edit `.components/`.

## Before anything

Run from the suite root (the directory with `manifests/components.lock.json`).

1. `uv run vclogic doctor`: every component must report `pinned and clean`.
   Otherwise ask the user to run `uv run vclogic init` (large download; it does not
   run models).
2. Memory generation and assessment spend money (Codex/Claude usage, OpenRouter
   credit). Confirm with the user before starting them.
3. Never print, copy or commit `.env` values. Report a missing credential by name only.

## New investor

The collector wizard is a full-screen interactive terminal UI for identity
confirmation, source triage and voice references. You cannot operate it. Ask the
user to run it in this session with the `!` prefix:

```
! uv run vclogic collect --name "Investor Name"
```

The wizard prints the workspace slug, and the slug can include the firm name.
List `workspace/research/traces/` to find it if needed. Collection is finished
when `traces/<slug>/guided_state.json` lists `finish`. If it does not, the user
reruns the same command with `--investor <slug>` to resume.

Then continue unattended:

```bash
uv run vclogic run --investor <slug>
```

`run` skips finished stages. It builds the memory (`investor-memory full-build`),
validates it, prepares and checks the onboarding bundle, and installs it into
`workspace/research/pipeline/`. The web app then lists the investor automatically.

Memory generation uses a local harness, Codex or Claude Code. Shell calls from an
agent are non-interactive, so `harness = "auto"` stops when both are installed.
Then ask the user which one to use and run the memory stage explicitly:
`uv run vclogic memory --investor <slug> -- --harness claude`.
Rerun `run` afterwards.

If the user types the whole flow themselves, `! uv run vclogic run --name "Investor Name"`
does collection and everything after it in one command.

## Assess a pitch

```bash
uv run vclogic assess --investor <slug> --pitch /abs/path/pitch.txt --company "Company"
```

This runs Phase 1 (rationale investigation) and Phase 2 (decision synthesis), then
prints the assessment. Markdown and JSON copies are saved under
`workspace/research/assessments/<slug>/<session>.*`. `--company` is required; it
excludes the company's own material from retrieval. Pass every known alias with
another `--company`. Report the decision and controlling rationales with their
evidence IDs. Do not invent scores the output does not contain.

## Web interface

`uv run vclogic web` serves the UI (port from `vclogic.toml`) for all
installed investors. It runs until stopped, so start it in the background. Newly onboarded
investors appear without a restart.

## When something fails

Stages stop on the first nonzero native exit. Quote the native error, name the
stage, and give the resume command. Never delete `wiki/<slug>` or a bundle to retry.
Those outputs are never overwritten, so ask the user before choosing a new
`--workspace`. Structural validation does not prove the memory is semantically
correct. Say so when reporting success.

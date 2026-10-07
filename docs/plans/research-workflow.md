# Suite research workflow

The suite will delegate scientific work to the pinned component CLIs. Commands
`discover`, `collect`, `process`, `memory`, `onboard`, and `pipeline` share paths
under `workspace/research/`: `traces/<slug>`, `wiki/<slug>`, `bundles/<slug>`,
`memory-cache/<slug>`, and `pipeline/`. Existing `assess` and `web` consume the
installed pipeline workspace. Collector discovery/download use its interactive
wizard so identity, source and budget choices stay explicit. Processing exports
and verifies the corpus. Memory uses the explicitly documented full-export
review route, not the incompatible legacy curated import route. Onboarding
preserves native configs, capability flags and validation. Pipeline runs native
preflight, run and verify; arbitrary new pitches use rehearsal/assess.

A root `.env` is loaded only for research commands. Existing shell variables
win, expansion is disabled, values are never copied into component repositories
or reports, and the original process environment is restored after dispatch.
No-key tests/demo never load this file. Codex authentication, local models,
optional AV dependencies and human evidence review remain native prerequisites.

Native subprocesses retain terminal interaction and return failures immediately.
Suite-owned path arguments cannot be overridden by forwarded native options.
No pipeline command invents evaluation data, confirms identities automatically,
or claims that a valid partial bundle is assessment-ready. Live generation
retains explicit --allow-paid opt-in. Native options are passed after `--`.

Validation: tests for environment precedence/restoration and no-key isolation,
argument construction and handoffs, failure short-circuiting, path containment,
credential diagnostics, and a real frozen-memory onboarding check without models.
No live collection or paid generation is required to test orchestration.

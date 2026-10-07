# Troubleshooting

Run `uv run vclogic doctor` and inspect the failing stage's log beneath the run directory. Keep diagnostics and hashes with a report, but remove credentials before sharing logs from live research.

| Symptom | Explanation and next step |
|---|---|
| First offline run fails | Exact sources/environments are absent. Run `uv run vclogic bootstrap --profile core` with setup network access first, or use a prebuilt core image. |
| Wrong origin, SHA or dirty component | The suite refuses drift. Preserve your edits and use a fresh `--components-dir` before the subcommand; do not reset an unrelated checkout. |
| `ready_for_assessment=false` after demo onboarding | Expected: `--skip-indexes` was selected. This partial bundle cannot serve live assessment. |
| Verification fails after editing outputs | Restore the original full run from a trusted copy or create a fresh run. Do not update hashes merely to conceal the mismatch. |
| Locked dependency installation fails | Check uv/Python versions, connectivity and platform wheel support. Keep committed locks intact and retain the error for diagnosis. |
| Missing credential in live mode | Export the key named by the chosen native provider config. The default demo needs no key. |
| Web health passes but no investor is usable | HTTP health does not prove asset readiness. Install a checked bundle with complete compatible indexes and query embedding runtime. |
| Fake index rejected by real embedding configuration | Index model identity and normalization/prefix settings must match the query embedder. Build the correct index in an explicitly prepared research workspace. |
| Onboarding installation conflicts | Native installation refuses differing existing files. Use a new workspace for a different bundle version and retain the prior provenance. |
| Memory source import rejects legacy evidence | See the audit's legacy text-field and attribution-status incompatibilities. Do not silently change admission policy or relabel evidence. |

The existing fake provider is specific to Elizabeth/Thoras and its legacy contract. It cannot assess an arbitrary pitch, provide a free generic web rehearsal, or produce a decision for a Phase-1-only contract. See [the full workflow](full-pipeline.md) for supported opt-in research boundaries.

The audit recorded three collector base-test failures in optional pyannote detection; these are not proof that the core reviewer path requires AV models. Avoid installing every optional extra to hide an unrelated failure.

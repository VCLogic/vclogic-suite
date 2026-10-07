# CPU reviewer container

The default container runs the suite's staged reviewer demonstration once, then exits. It validates a frozen memory, performs wiki-only onboarding, and runs the assessment component's scripted example. This checks software integration; it does not reproduce publication metrics or predict investment decisions with a real model.

From the repository root:

```bash
mkdir -p workspace
docker compose up --build --abort-on-container-exit --exit-code-from core
```

Building requires network access to image registries, Debian, GitHub and Python package sources. The build fetches exact component commits from `manifests/components.lock.json` and installs their locked lightweight environments. Host checkouts, credentials and workspace files are excluded from the build context. No torch extras, model weights, AV tools or frontend are installed.

Execution has `network_mode: none`, a read-only image filesystem, a temporary writable `/tmp`, and a writable `./workspace` mount. Reports are written beneath `workspace/runs/<run-id>/report.json`; `workspace/latest.json` points to the latest run. Component sources stay inside the image. The default process runs as root, so Linux bind-mount output may be root-owned.
Inspect an existing run using the same installed environment:

```bash
docker compose run --rm core uv run --no-sync vclogic --workspace /workspace verify
```

`docker compose up` builds and executes the core job; it does not start a website. To rerun without building, use `docker compose run --rm core`. Deleting containers does not delete the bind-mounted workspace.

## Pins and reproducibility boundary

Registry index digests were resolved using `docker buildx imagetools inspect` on 2026-10-07:

| Image | Index SHA256 |
| --- | --- |
| `python:3.12.12-slim-bookworm` | `593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c` |
| `ghcr.io/astral-sh/uv:0.9.17` | `5cb6b54d2bc3fe2eb9a8483db958a0b9eebf9edff68adedb369df8e7b98711a2` |

The corresponding Linux AMD64 manifest digests are `2986c55feb36e6cae00fa1fefb454283e4b33f35e75ff8bdd123b134130be301` and `e64e0ddf4bd05ffaca0b3c35c80971b848d2c733b4979267747567ca2f2a2cb0`, respectively. Other platforms are not certified by the AMD64 test. Dependency locks and Git SHAs do not freeze Debian repository packages or unbounded upstream build-system requirements. Archive the finished image and its digest for exact runtime replay. A cold offline build is unsupported; a built image runs the demonstration offline.

## Optional web and research execution

A web container/profile is deferred. Use the suite's native `bootstrap --profile web` and `web` commands described in the research guide. Web requires Node 22.12 or newer to build its existing frontend, a prepared assessment-ready workspace with compatible indexes, and explicit credential/cost opt-in for live inference. The wiki-only onboarding stage deliberately lacks those indexes. HTTP health alone does not establish investor readiness, and this suite does not provide a free interactive fake rehearsal. Never put provider keys into build arguments or image layers.

## Continuous integration

`.github/workflows/ci.yml` pins checkout/setup-uv actions by full SHA, runs locked suite tests, bootstraps the real core revisions, enables integration tests with `VCLOGIC_INTEGRATION=1`, and builds/runs the offline Compose job. No model calls or provider credentials are needed. Upstream component regression suites and optional live/AV/browser tests are separate from this smoke test.

## Executed container validation

On 2026-10-07, the core image built and ran successfully using Docker 24.0.4 on Linux AMD64. The container's inspected settings confirmed network mode `none` and a read-only root filesystem. The report recorded 30.022 seconds for the staged demo; a second container verified the persisted run with `valid=true`. This is one local measurement, not a performance guarantee. The first built image occupied 1,616,914,215 bytes (about 1.51 GiB uncompressed), including exact source checkouts and their environments. No publication reproduction was available.

The development environment uses a Docker daemon with its own host filesystem: the test bind mount at `/tmp/vclogic-docker-output` was accessible through Docker containers, not directly from the tool shell. Persistence was checked by the separate verification container and the report was copied out through `docker compose run … cat`. With a remote Docker daemon, bind paths refer to the daemon host; retrieve reports there or through a container. Ordinary local Docker installations expose `./workspace` directly on the local host.

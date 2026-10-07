# Registry index digests verified 2026-10-07; see docs/docker.md.
FROM ghcr.io/astral-sh/uv:0.9.17@sha256:5cb6b54d2bc3fe2eb9a8483db958a0b9eebf9edff68adedb369df8e7b98711a2 AS uv
FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
COPY --from=uv /uv /uvx /usr/local/bin/
# OS packages use Debian repositories; archive the built image for exact replay.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /opt/vclogic
COPY pyproject.toml uv.lock .python-version ./
COPY src/ src/
COPY manifests/ manifests/
COPY README.md ./
RUN uv sync --locked && uv run --no-sync vclogic bootstrap --profile core
# The image contains only the lightweight locked component environments.
# No credential, live provider, model weights or host component tree is copied.
RUN mkdir -p /workspace
ENV UV_OFFLINE=1
CMD ["uv", "run", "--no-sync", "vclogic", "--workspace", "/workspace", "demo", "--offline"]

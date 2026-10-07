"""Executed inside a component environment; calls its validators without loading models."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


def offline_embedding_identity(settings):
    """Ask native providers for their identity with injected inert model/client objects."""
    from vc_clone_graph.providers.base import embedding_identity
    from vc_clone_graph.providers.ollama import OllamaProvider
    from vc_clone_graph.providers.sentence_transformers import SentenceTransformerEmbeddingProvider

    if settings.kind == "ollama":
        if not settings.base_url:
            raise ValueError("Ollama embeddings require embedding.base_url")
        provider = OllamaProvider(
            "embedding-only", settings.model, settings.base_url, client=object()
        )
    elif settings.kind == "sentence_transformers":
        provider = SentenceTransformerEmbeddingProvider(
            settings.model,
            revision=settings.revision,
            device=settings.device,
            batch_size=settings.batch_size,
            normalize=settings.normalize,
            document_prefix=settings.document_prefix,
            query_prefix=settings.query_prefix,
            model_instance=object(),
        )
    else:
        raise ValueError("Rehearsal embeddings must be local")
    return SimpleNamespace(metadata=embedding_identity(provider))


def main() -> None:
    from vc_clone_graph.rehearsal_config import load_rehearsal_config

    workspace, path, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    try:
        config = load_rehearsal_config(path, workspace=workspace)
        if mode == "web":
            from vclogic_web.investor_catalog import InvestorCatalog

            # Refresh only: no provider, model construction or web service is started.
            data = InvestorCatalog(workspace=workspace, config=config).refresh()
            available = [r for r in data["investors"] if r["available"] and r["enabled"]]
            errors = data["discovery_errors"] + [
                str(v.get("error"))
                for r in data["investors"]
                for v in r["versions"]
                if v.get("error")
            ]
            print(
                json.dumps(
                    {"ready": bool(available), "errors": errors or ["No ready investor selected"]}
                )
            )
            return
        from vc_clone_graph.firewall import safe_slug
        from vc_clone_graph.rehearsal_runtime import (
            _load_portfolio,
            _load_precedents,
            _registry_profile,
            _taxonomy,
        )
        from vc_clone_graph.retrieval import HybridWikiIndex

        slug = safe_slug(sys.argv[4])
        root = config.resolve_path(config.rehearsal.input_root)
        profile = _registry_profile(root, root / "investors" / f"{slug}.toml")
        _taxonomy(root / config.rehearsal.taxonomy_path)
        if config.embedding is None:
            raise ValueError("Research adapter requires explicit pinned embedding configuration")
        identity = offline_embedding_identity(config.embedding)
        HybridWikiIndex.load(
            root / "indexes" / f"{slug}.json",
            profile.wiki_path,
            identity,
            require_complete_embeddings=True,
        )
        if (
            config.precedents.enabled
            and not (root / "indexes" / f"{slug}.precedents.json").is_file()
        ):
            raise ValueError("Precedent index missing; prepare it before live assessment")
        _load_precedents(
            config, root, slug, identity, excluded_episode_slug=None, excluded_aliases=()
        )
        _load_portfolio(config, root, slug, identity, excluded_episode_slug=None)
        print(json.dumps({"ready": True, "errors": []}))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"ready": False, "errors": [str(error)]}))


if __name__ == "__main__":
    main()

"""Exact Git acquisition; never overwrite an existing checkout or follow a branch."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Component:
    id: str
    repository: str
    commit: str
    directory: str
    package: str
    version: str
    role: str


def load_components(path: Path) -> dict[str, Component]:
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1 or not isinstance(data.get("components"), list):
        raise ValueError("Unsupported components manifest")
    result = {}
    directories = set()
    for row in data["components"]:
        component = Component(**row)
        if (
            not re.fullmatch(r"[0-9a-f]{40}", component.commit)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", component.directory)
            or not re.fullmatch(r"[a-z][a-z0-9-]*", component.id)
            or not re.fullmatch(r"https://github.com/VCLogic/[a-z0-9-]+\.git", component.repository)
        ):
            raise ValueError("Invalid component SHA, URL or checkout directory")
        if component.id in result or component.directory in directories:
            raise ValueError("Duplicate component identity or directory")
        result[component.id] = component
        directories.add(component.directory)
    if not result:
        raise ValueError("Empty components manifest")
    return result


def _git(path: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(path), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if process.returncode:
        # Do not echo transport stderr: credential helpers/URLs can contain secrets.
        raise ValueError(f"Git {args[0]} failed in {path}; check access and the pinned revision")
    return process.stdout.strip()


def verify_component(component: Component, root: Path) -> Path:
    target = root / component.directory
    if target.is_symlink():
        raise ValueError(f"Component checkout cannot be a symlink: {target}")
    if not (target / ".git").is_dir():
        raise ValueError(f"Missing component {component.id}; run vclogic bootstrap")
    if _git(target, "remote", "get-url", "origin") != component.repository:
        raise ValueError(f"Wrong origin for {component.id}; move this checkout aside explicitly")
    if _git(target, "rev-parse", "HEAD") != component.commit:
        raise ValueError(f"Wrong revision for {component.id}; expected {component.commit}")
    if _git(target, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError(f"Component {component.id} is modified; refusing to overwrite or run it")
    return target


def ensure_component(component: Component, root: Path, *, offline: bool = False) -> Path:
    target = root / component.directory
    if target.exists() or target.is_symlink():
        return verify_component(component, root)
    if offline:
        raise ValueError(f"Missing {component.id} in offline mode; run bootstrap online first")
    root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{component.id}-", dir=root))
    try:
        _git(temporary, "init", "--quiet")
        _git(temporary, "remote", "add", "origin", component.repository)
        _git(temporary, "fetch", "--quiet", "--depth", "1", "origin", component.commit)
        _git(temporary, "checkout", "--quiet", "--detach", component.commit)
        if _git(temporary, "rev-parse", "HEAD") != component.commit:
            raise ValueError(f"Fetched wrong revision for {component.id}")
        temporary.rename(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return verify_component(component, root)

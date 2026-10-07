"""File inventories and checked copies, not new scientific artifact formats."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path, PurePosixPath


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    value = PurePosixPath(relative)
    if (
        not relative
        or value.is_absolute()
        or ".." in value.parts
        or "\\" in relative
        or str(value) != relative
        or any(ord(c) < 32 for c in relative)
    ):
        raise ValueError(f"Unsafe artifact path: {relative!r}")
    current = root
    if root.is_symlink():
        raise ValueError(f"Artifact root cannot be a symlink: {root}")
    for part in value.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Artifact path cannot contain a symlink: {relative}")
    return current


def verify_files(root: Path, hashes: dict[str, str]) -> None:
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Empty or invalid artifact inventory")
    for relative, expected in hashes.items():
        path = safe_path(root, relative)
        if (
            not re.fullmatch(r"[0-9a-f]{64}", expected)
            or not path.is_file()
            or digest(path) != expected
        ):
            raise ValueError(f"Artifact hash mismatch: {relative}")


def copy_verified(source: Path, target: Path, hashes: dict[str, str]) -> None:
    verify_files(source, hashes)
    for relative in hashes:
        destination = safe_path(target, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError(f"Refusing to replace artifact: {destination}")
        shutil.copyfile(safe_path(source, relative), destination)
    verify_files(target, hashes)


def inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob("*")) if p.is_file()
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)

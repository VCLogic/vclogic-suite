"""Public suite CLI: acquisition, execution and validation of existing components."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .components import ensure_component, verify_component
from .runtime import Context, bootstrap


def find_root(explicit: Path | None) -> Path:
    if explicit is not None:
        candidates = [explicit.resolve()]
    else:
        candidates = [Path.cwd(), *Path.cwd().parents]
    for path in candidates:
        if (path / "manifests/components.lock.json").is_file():
            return path
    raise ValueError("Run from the vclogic-suite checkout or supply --root PATH")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="vclogic", description=__doc__)
    root.add_argument("--root", type=Path, help="Suite checkout containing manifests")
    root.add_argument("--components-dir", type=Path, help="Component checkout parent")
    root.add_argument("--workspace", type=Path, help="Suite runtime output root")
    commands = root.add_subparsers(dest="command", required=True)
    components = commands.add_parser("components", help="List all exact component revisions")
    components.add_argument("--fetch", action="store_true", help="Fetch all pinned revisions")
    components.add_argument("--offline", action="store_true")
    setup = commands.add_parser(
        "bootstrap", help="Fetch components and install locked environments"
    )
    setup.add_argument("--profile", choices=("core", "web", "all"), default="core")
    setup.add_argument("--offline", action="store_true")
    commands.add_parser("doctor", help="Inspect local tools/checkouts without external requests")
    demo = commands.add_parser(
        "demo", help="No-key reviewer demo; separate partial onboarding and mock assessment"
    )
    demo.add_argument("--offline", action="store_true", help="Never fetch components/dependencies")
    verify = commands.add_parser(
        "verify", help="Revalidate a saved demo through component validators"
    )
    verify.add_argument("--run", type=Path)
    for name in ("assess", "web"):
        command = commands.add_parser(
            name, help="Explicit live operation on a prepared research workspace"
        )
        command.add_argument("--workspace", dest="research_workspace", type=Path, required=True)
        command.add_argument("--config", type=Path, required=True, help="Native rehearsal TOML")
        command.add_argument(
            "--allow-paid", action="store_true", help="Permit configured provider-backed operations"
        )
        if name == "assess":
            command.add_argument("--investor", required=True)
            command.add_argument("--pitch", type=Path, required=True)
            command.add_argument("--company", action="append", default=[])
        else:
            command.add_argument("--port", type=int, default=8000)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = find_root(args.root)
        ctx = Context(
            root,
            (args.components_dir or root / ".components").resolve(),
            (args.workspace or root / "workspace").resolve(),
        )
        if args.command == "components":
            rows = []
            for item in ctx.components.values():
                if args.fetch:
                    ensure_component(item, ctx.components_dir, offline=args.offline)
                rows.append(asdict(item))
            result = {"components": rows}
        elif args.command == "bootstrap":
            result = bootstrap(ctx, args.profile, offline=args.offline)
        elif args.command == "doctor":
            status = {}
            for name, item in ctx.components.items():
                try:
                    verify_component(item, ctx.components_dir)
                    status[name] = "pinned and clean"
                except ValueError as error:
                    status[name] = str(error)
            result = {
                "python": sys.version.split()[0],
                "tools": {t: shutil.which(t) for t in ("uv", "git", "docker", "npm")},
                "components": status,
                "network_requests": False,
                "note": "HTTP health and checkout availability do not prove investor readiness.",
            }
        elif args.command == "demo":
            from .demo import demo

            report = demo(ctx, offline=args.offline)
            result = {
                key: report[key]
                for key in (
                    "run_directory",
                    "validation_passed",
                    "paid_inference",
                    "stages",
                    "publication",
                )
            }
        elif args.command == "verify":
            from .verification import verify_run

            result = verify_run(ctx, args.run)
        else:
            from .research import launch

            return launch(ctx, args)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; existing run artifacts are retained.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

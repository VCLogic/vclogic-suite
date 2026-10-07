"""One suite-owned dotenv boundary for live research subprocesses."""

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import dotenv_values


@contextmanager
def research_environment(root: Path):
    # No shell evaluation or interpolation; shell-exported values take precedence.
    values = dotenv_values(root / ".env", interpolate=False)
    added = {
        key: value for key, value in values.items() if value is not None and key not in os.environ
    }
    previous_disabled = os.environ.get("PYTHON_DOTENV_DISABLED")
    os.environ.update(added)
    # Prevent component-local dotenv auto-discovery from introducing another file.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    try:
        yield
    finally:
        for key in added:
            os.environ.pop(key, None)
        if previous_disabled is None:
            os.environ.pop("PYTHON_DOTENV_DISABLED", None)
        else:
            os.environ["PYTHON_DOTENV_DISABLED"] = previous_disabled

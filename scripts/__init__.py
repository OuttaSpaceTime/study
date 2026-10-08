"""Entry scripts re-exec into the project venv when started with another python.

Every script here has the shebang `uv run python3`, and inserts the repo root
and imports `scripts.*` before any third-party package, so this runs first.
Inside the repo `uv run` already picks .venv; from another directory it starts
a bare interpreter, and fastanki or yaml is missing. Prefixes are compared,
not resolved executables: .venv/bin/python3 is a symlink to that same
uv-managed interpreter, so both resolve to one file.

Only an entry script in this directory is re-exec'd. Other programs import
this package from their own venv (omvida's wiki service imports scripts.wiki),
and replacing their process with this repo's python would break them.
"""

import os
import sys

from .config import REPO_ROOT

_VENV = REPO_ROOT / ".venv"
_VENV_PY = _VENV / "bin" / "python3"
# argv[0] is "" in an interactive or -c interpreter; "" would resolve to cwd.
_entry = os.path.realpath(sys.argv[0]) if sys.argv[0] else ""

if (
    os.path.dirname(_entry) == str(REPO_ROOT / "scripts")
    # No venv (a fresh clone before `uv sync`): run as-is and let the import fail.
    and _VENV_PY.exists()
    and os.path.realpath(sys.prefix) != os.path.realpath(_VENV)
):
    os.execv(str(_VENV_PY), [str(_VENV_PY), _entry, *sys.argv[1:]])

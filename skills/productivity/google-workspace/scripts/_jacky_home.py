"""Resolve JACKY_HOME for standalone skill scripts.

Skill scripts may run outside the Jacky process (e.g. system Python,
nix env, CI) where ``jacky_constants`` is not importable.  This module
provides the same ``get_jacky_home()`` and ``display_jacky_home()``
contracts as ``jacky_constants`` without requiring it on ``sys.path``.

When ``jacky_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``jacky_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``JACKY_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from jacky_constants import display_jacky_home as display_jacky_home
    from jacky_constants import get_jacky_home as get_jacky_home
except (ModuleNotFoundError, ImportError):

    def get_jacky_home() -> Path:
        """Return the Jacky home directory (default: ~/.jacky).

        Mirrors ``jacky_constants.get_jacky_home()``."""
        val = os.environ.get("JACKY_HOME", "").strip()
        return Path(val) if val else Path.home() / ".jacky"

    def display_jacky_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``jacky_constants.display_jacky_home()``."""
        home = get_jacky_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)

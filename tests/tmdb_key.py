"""Find a TMDB read token for tests that talk to the real TMDB.

The token is never stored in this repo. Tests look for it, in order:

1. the ``TMDB_API_READ_KEY`` environment variable
2. ``TMDB_API_READ_KEY`` in ``$XDG_CONFIG_HOME/discripper/tmdb.env``
   (``~/.config/discripper/tmdb.env`` when ``XDG_CONFIG_HOME`` isn't set)

Without one, tests marked ``@requires_tmdb_key`` are skipped.
"""

import os
import unittest
from pathlib import Path

from dotenv import dotenv_values

KEY_NAME = "TMDB_API_READ_KEY"


def key_file():
    config_home = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config_home) / "discripper" / "tmdb.env"


def tmdb_read_key():
    """The TMDB read token, or None when there isn't one on this machine."""
    if os.environ.get(KEY_NAME):
        return os.environ[KEY_NAME]
    if key_file().is_file():
        return dotenv_values(key_file()).get(KEY_NAME) or None
    return None


requires_tmdb_key = unittest.skipUnless(
    tmdb_read_key(), f"no TMDB read token: set {KEY_NAME} or put it in {key_file()}")

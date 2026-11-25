"""Replay TMDB responses recorded by scripts/record_tmdb_fixtures.py."""

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tmdb"


class ReplayTmdb:
    """Fetch seam adapter that answers with a recording, in order.

    A request that doesn't match the next recorded path and params fails the
    test, so it also catches Media lookup asking TMDB for something new.
    """

    def __init__(self, name):
        self.name = name
        self.exchanges = json.loads((FIXTURES / f"{name}.json").read_text())

    def __call__(self, path, params):
        if not self.exchanges:
            raise AssertionError(f"{self.name}: unexpected TMDB request {path} {params}")
        expected = self.exchanges.pop(0)
        if (path, params) != (expected["path"], expected["params"]):
            raise AssertionError(f"{self.name}: asked TMDB for {path} {params}, "
                                 f"recorded {expected['path']} {expected['params']}")
        return expected["response"]

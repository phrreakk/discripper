#!/usr/bin/env python
"""Record real TMDB responses as test fixtures in tests/fixtures/tmdb/.

    uv run python scripts/record_tmdb_fixtures.py

Needs a TMDB read token (see tests/tmdb_key.py). Each scenario runs a real
MediaLookup call and saves every TMDB exchange it made: the path, the params,
and the response trimmed to the fields Media lookup reads. Request headers,
and so the token, are never saved.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from media_lookup import Media, MediaLookup, tmdb_fetch  # noqa: E402
from tests.tmdb_fixtures import FIXTURES  # noqa: E402
from tests.tmdb_key import KEY_NAME, key_file, tmdb_read_key  # noqa: E402

# The only TMDB fields Media lookup reads; everything else is dropped. If Media lookup
# starts reading a new field, add it here and re-record.
FIELDS_MEDIA_LOOKUP_READS = {"total_results", "results", "id", "popularity", "original_title", "release_date",
        "original_name", "first_air_date", "seasons", "season_number", "name", "air_date",
        "episodes", "episode_number", "runtime"}

SCENARIOS = {
    "find_movie_how_to_train_your_dragon_2010":
        lambda lookup: lookup.find("movie", "How to Train Your Dragon", 2010),
    "get_movie_10191": lambda lookup: lookup.get("movie", 10191),
    "find_tv_dreamworks_dragons": lambda lookup: lookup.find("tv", "DreamWorks Dragons", ""),
    "seasons_tv_44305": lambda lookup: lookup.seasons(Media("tv", 44305, "DreamWorks Dragons", "2012")),
    "episodes_tv_44305_season_1":
        lambda lookup: lookup.episodes(Media("tv", 44305, "DreamWorks Dragons", "2012"), 1),
}


def trim(value):
    if isinstance(value, dict):
        return {key: trim(item) for key, item in value.items() if key in FIELDS_MEDIA_LOOKUP_READS}
    if isinstance(value, list):
        return [trim(item) for item in value]
    return value


def record(fetch, scenario):
    exchanges = []

    def recording_fetch(path, params):
        response = fetch(path, params)
        exchanges.append({"path": path, "params": params, "response": trim(response)})
        return response

    scenario(MediaLookup(recording_fetch))
    return exchanges


def main():
    key = tmdb_read_key()
    if not key:
        sys.exit(f"No TMDB read token: set {KEY_NAME} or put it in {key_file()}")
    fetch = tmdb_fetch(key)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name, scenario in SCENARIOS.items():
        path = FIXTURES / f"{name}.json"
        path.write_text(json.dumps(record(fetch, scenario), indent=2, ensure_ascii=False) + "\n")
        print(f"Recorded {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""Media lookup: find Media and Seasons on TMDB.

The only dependency is ``fetch(path, params) -> dict``, which performs a GET
against the TMDB v3 API (``path`` is relative, e.g. ``"search/movie"``) and
returns the decoded JSON.
"""

from dataclasses import dataclass
from typing import Literal

import requests

Kind = Literal["movie", "tv"]


@dataclass(frozen=True)
class Media:
    kind: Kind
    tmdb_id: int
    name: str
    year: str


@dataclass(frozen=True)
class Season:
    tmdb_id: int
    number: int
    name: str
    air_date: str


@dataclass(frozen=True)
class SearchResult:
    media: Media
    popularity: float


# A search with more results than this is too broad to pick from.
MAX_RESULTS = 25


class MediaLookupError(Exception):
    """Base class for everything Media lookup raises."""


class LookupFailed(MediaLookupError):
    """TMDB could not be reached or refused the request."""


class NoResults(MediaLookupError):
    """The search matched no Media."""


class TooManyResults(MediaLookupError):
    """The search matched more than MAX_RESULTS Media."""

    def __init__(self, year_given):
        super().__init__(f"more than {MAX_RESULTS} results")
        self.year_given = year_given


class MediaLookup:
    def __init__(self, fetch):
        self._fetch = fetch

    def find(self, kind, name, year):
        _check_kind(kind)
        params = {"query": name, "include_adult": "false", "language": "en-US", "page": 1}
        if year:
            params["year"] = year
        response = self._fetch(f"search/{kind}", params)
        if response["total_results"] == 0:
            raise NoResults()
        if response["total_results"] > MAX_RESULTS:
            raise TooManyResults(year_given=bool(year))
        results = [SearchResult(_media(kind, row), row["popularity"]) for row in response["results"]]
        return sorted(results, key=lambda result: result.popularity, reverse=True)

    def get(self, kind, tmdb_id):
        _check_kind(kind)
        return _media(kind, self._fetch(f"{kind}/{tmdb_id}", {"language": "en-US"}))

    def seasons(self, show):
        if show.kind != "tv":
            raise ValueError(f"Only TV shows have seasons, not {show.kind}")
        response = self._fetch(f"tv/{show.tmdb_id}", {"language": "en-US"})
        seasons = [Season(int(row["id"]), row["season_number"], row["name"], row.get("air_date") or "")
                   for row in response["seasons"]]
        return sorted(seasons, key=lambda season: season.number)


# TMDB names the same facts differently for movies and shows.
_FIELDS = {
    "movie": ("original_title", "release_date"),
    "tv": ("original_name", "first_air_date"),
}


def _check_kind(kind):
    if kind not in _FIELDS:
        raise ValueError(f"Unknown media type: {kind}")


def _media(kind, row):
    name_field, date_field = _FIELDS[kind]
    return Media(kind, int(row["id"]), row[name_field], (row.get(date_field) or "")[:4])


TMDB_API = "https://api.themoviedb.org/3/"


def tmdb_fetch(api_key):
    """The production adapter for the fetch seam: HTTP GET against TMDB with a read token."""
    headers = {"accept": "application/json", "Authorization": f"Bearer {api_key}"}

    def fetch(path, params):
        try:
            response = requests.get(TMDB_API + path, params=params, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as err:
            raise LookupFailed(str(err)) from err
        return response.json()

    return fetch

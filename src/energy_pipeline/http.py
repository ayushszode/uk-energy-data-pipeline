"""HTTP helper with retries, so one slow response does not break a refresh."""
from __future__ import annotations

import time

import requests

from .config import HTTP_TIMEOUT, USER_AGENT

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, text/csv, */*"})


class HttpError(RuntimeError):
    def __init__(self, url: str, status: int, body: str):
        super().__init__(f"HTTP {status} for {url}: {body[:200]}")
        self.status = status


def get(url: str, params: dict | None = None, retries: int = 4, pause: float = 0.2) -> requests.Response:
    """GET with exponential backoff on network errors, 429 and 5xx responses."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = _session.get(url, params=params, timeout=HTTP_TIMEOUT)
        except requests.RequestException as exc:  # network problem: retry
            last_exc = exc
        else:
            if resp.status_code == 200:
                time.sleep(pause)  # be polite to free public APIs
                return resp
            if resp.status_code not in (429, 500, 502, 503, 504):
                raise HttpError(url, resp.status_code, resp.text)
            last_exc = HttpError(url, resp.status_code, resp.text)
        time.sleep(2 ** attempt)
    raise RuntimeError(f"Giving up on {url}: {last_exc}")

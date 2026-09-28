"""Shared HTTP session with retry + backoff."""
import logging
import time

import requests

from src.config import USER_AGENT

log = logging.getLogger("http")


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def get_json(session: requests.Session, url: str, params: dict, retries: int = 5) -> dict:
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code} from {url}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            wait = 2 ** attempt
            log.warning("request failed (%s); retry %d/%d in %ds", e, attempt + 1, retries, wait)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}")

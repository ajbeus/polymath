"""bioRxiv ingest via the public details API (no key). https://api.biorxiv.org/details/biorxiv/<from>/<to>/<cursor>

The API has no keyword search: it lists every preprint posted in a date range, 100 per page. So this
module yields everything in the window and the caller keeps only papers that match a lens.
A preprint appears once per version; we keep the newest version of each DOI.
"""

import json
import time
from datetime import date, timedelta
from typing import Iterator

import requests

from ..config import USER_AGENT
from . import PaperRecord

API_URL = "https://api.biorxiv.org/details/biorxiv"
PAGE_SIZE = 100
DELAY_SECONDS = 1.0


def parse_item(item: dict) -> PaperRecord:
    doi = item["doi"].strip()
    authors = [a.strip() for a in (item.get("authors") or "").split(";") if a.strip()]
    category = (item.get("category") or "").strip()
    return PaperRecord(
        id=f"biorxiv:{doi}",
        source="biorxiv",
        external_id=doi,
        title=" ".join((item.get("title") or "").split()),
        abstract=" ".join((item.get("abstract") or "").split()),
        published=(item.get("date") or "")[:10],
        authors=authors,
        url=f"https://www.biorxiv.org/content/{doi}",
        doi=doi,
        categories=[category] if category else [],
        extras={"version": item.get("version"), "type": item.get("type")},
        raw_format="biorxiv-json",
        raw_body=json.dumps(item, ensure_ascii=False),
    )


def _get(session: requests.Session, url: str) -> dict:
    for attempt in range(4):
        try:
            resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"{resp.status_code} from bioRxiv")
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt * 2)
    raise AssertionError("unreachable")


def fetch(days: int, session: requests.Session | None = None) -> Iterator[PaperRecord]:
    """Every bioRxiv preprint posted in the last `days` days (latest version of each), newest pages last."""
    session = session or requests.Session()
    end = date.today()
    start = end - timedelta(days=days)
    latest: dict[str, dict] = {}
    cursor = 0
    while True:
        data = _get(session, f"{API_URL}/{start.isoformat()}/{end.isoformat()}/{cursor}/json")
        items = data.get("collection") or []
        if not items:
            break
        for item in items:
            prev = latest.get(item["doi"])
            if prev is None or int(item.get("version") or 0) >= int(prev.get("version") or 0):
                latest[item["doi"]] = item
        cursor += len(items)
        total = int((data.get("messages") or [{}])[0].get("total") or 0)
        if cursor >= total:
            break
        time.sleep(DELAY_SECONDS)
    for item in latest.values():
        yield parse_item(item)

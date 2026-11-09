"""arXiv ingest via the public Atom API (no key). Be polite: arXiv asks for one request per 3 seconds."""

import re
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Iterator

import requests

from ..config import USER_AGENT
from ..models import LensConfig
from . import PaperRecord

API_URL = "https://export.arxiv.org/api/query"
PAGE_SIZE = 100
DELAY_SECONDS = 3.1
NS = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}


def build_query(lens: LensConfig) -> str | None:
    """(cat:A OR cat:B) AND (all:"kw1" OR all:"kw2"). Keywords are skipped if useKeywords is false."""
    cfg = lens.arxiv or {}
    cats = cfg.get("categories") or []
    if not cats:
        return None
    query = "(" + " OR ".join(f"cat:{c}" for c in cats) + ")"
    if cfg.get("useKeywords", True) and lens.keywords:
        query += " AND (" + " OR ".join(f'all:"{k}"' for k in lens.keywords) + ")"
    return query


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_entry(entry: ET.Element) -> PaperRecord:
    abs_url = _clean(entry.findtext("a:id", namespaces=NS))
    arxiv_id = re.sub(r"v\d+$", "", abs_url.rsplit("/abs/", 1)[-1])
    doi = entry.findtext("x:doi", namespaces=NS)
    return PaperRecord(
        id=f"arxiv:{arxiv_id}",
        source="arxiv",
        external_id=arxiv_id,
        title=_clean(entry.findtext("a:title", namespaces=NS)),
        abstract=_clean(entry.findtext("a:summary", namespaces=NS)),
        published=_clean(entry.findtext("a:published", namespaces=NS))[:10],
        authors=[_clean(a.findtext("a:name", namespaces=NS)) for a in entry.findall("a:author", NS)],
        url=f"https://arxiv.org/abs/{arxiv_id}",
        doi=_clean(doi) or None,
        categories=[c.get("term") for c in entry.findall("a:category", NS) if c.get("term")],
        raw_format="atom-entry",
        raw_body=ET.tostring(entry, encoding="unicode"),
    )


def fetch(lens: LensConfig, days: int, max_results: int, session: requests.Session | None = None) -> Iterator[PaperRecord]:
    """Newest-first papers for a lens, stopping at `days` back or `max_results`."""
    query = build_query(lens)
    if not query:
        return
    session = session or requests.Session()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    start = 0
    while start < max_results:
        params = {
            "search_query": query, "sortBy": "submittedDate", "sortOrder": "descending",
            "start": start, "max_results": min(PAGE_SIZE, max_results - start),
        }
        resp = session.get(API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
        resp.raise_for_status()
        entries = ET.fromstring(resp.text).findall("a:entry", NS)
        if not entries:
            return
        for entry in entries:
            if entry.find("a:id", NS) is None or "/api/errors" in (entry.findtext("a:id", namespaces=NS) or ""):
                raise RuntimeError(_clean(entry.findtext("a:summary", namespaces=NS)) or "arXiv API error")
            rec = parse_entry(entry)
            if rec.published < cutoff:
                return  # results are newest-first, so everything after this is older
            yield rec
        start += len(entries)
        time.sleep(DELAY_SECONDS)

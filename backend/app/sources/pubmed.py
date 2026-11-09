"""PubMed ingest: esearch to find PMIDs, efetch to get records.

parse_article / text_of are ported from abstract_parser.py. Added: authors, a full publication date
(PubMed's own "pubmed" history date rather than the journal year), and the esearch step so a lens
can discover papers on its own instead of needing a PMID list from the link hopper.
"""

import re
import time
import xml.etree.ElementTree as ET
from typing import Iterator

import requests

from ..config import NCBI_API_KEY, USER_AGENT
from ..models import LensConfig
from . import PaperRecord

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH_SIZE = 100  # PMIDs per efetch request


def text_of(el):
    """All text inside an element, including nested markup (<i>, <sub>...)."""
    return "".join(el.itertext()).strip() if el is not None else ""


def _pub_date(art) -> str:
    """YYYY-MM-DD the paper entered PubMed; falls back to the journal year (as Jan 1) if absent."""
    for d in art.findall("PubmedData/History/PubMedPubDate"):
        if d.get("PubStatus") == "pubmed":
            y, m, day = text_of(d.find("Year")), text_of(d.find("Month")), text_of(d.find("Day"))
            if y and m and day:
                return f"{y}-{int(m):02d}-{int(day):02d}"
    cit = art.find("MedlineCitation")
    year = text_of(cit.find("Article/Journal/JournalIssue/PubDate/Year"))
    if not year:  # older records use <MedlineDate>1993 Feb</MedlineDate>
        m = re.search(r"\d{4}", text_of(cit.find("Article/Journal/JournalIssue/PubDate/MedlineDate")))
        year = m.group(0) if m else "1900"
    return f"{year}-01-01"


def parse_article(art) -> PaperRecord:
    """Turn one <PubmedArticle> element into a PaperRecord."""
    cit = art.find("MedlineCitation")
    pmid = text_of(cit.find("PMID"))
    article = cit.find("Article")

    title = text_of(article.find("ArticleTitle"))

    # Structured abstracts have several labeled <AbstractText> parts.
    parts = []
    for at in article.findall("Abstract/AbstractText"):
        label = at.get("Label")
        body = text_of(at)
        parts.append(f"{label}: {body}" if label else body)
    abstract = "\n".join(p for p in parts if p)

    journal = text_of(article.find("Journal/Title"))
    mesh = [text_of(d) for d in cit.findall("MeshHeadingList/MeshHeading/DescriptorName")]

    authors = []
    for a in article.findall("AuthorList/Author"):
        last, initials = text_of(a.find("LastName")), text_of(a.find("Initials"))
        name = f"{last} {initials}".strip() or text_of(a.find("CollectiveName"))
        if name:
            authors.append(name)

    doi = pmcid = ""
    for aid in art.findall("PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi":
            doi = text_of(aid)
        elif aid.get("IdType") == "pmc":
            pmcid = text_of(aid)

    return PaperRecord(
        id=f"pubmed:{pmid}", source="pubmed", external_id=pmid, title=title, abstract=abstract,
        published=_pub_date(art), authors=authors, url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        doi=doi or None, categories=mesh,
        extras={"mesh": mesh, "journal": journal, "pmcid": pmcid},
        raw_format="pubmed-xml", raw_body=ET.tostring(art, encoding="unicode"),
    )


def _params(extra: dict) -> dict:
    return {**extra, **({"api_key": NCBI_API_KEY} if NCBI_API_KEY else {})}


def search_pmids(term: str, days: int, retmax: int, session: requests.Session) -> list[str]:
    resp = session.get(ESEARCH_URL, params=_params({
        "db": "pubmed", "term": term, "datetype": "edat", "reldate": days,
        "retmax": retmax, "retmode": "json", "sort": "date",
    }), headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    return resp.json()["esearchresult"]["idlist"]


def fetch(lens: LensConfig, days: int, max_results: int, session: requests.Session | None = None) -> Iterator[PaperRecord]:
    term = (lens.pubmed or {}).get("query")
    if not term:
        return
    session = session or requests.Session()
    delay = 0.11 if NCBI_API_KEY else 0.35  # stay under 10/s with a key, 3/s without
    pmids = search_pmids(term, days, max_results, session)
    time.sleep(delay)
    for i in range(0, len(pmids), BATCH_SIZE):
        batch = pmids[i:i + BATCH_SIZE]
        resp = session.post(EFETCH_URL, data=_params({"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}),
                            headers={"User-Agent": USER_AGENT}, timeout=60)  # POST: long id lists
        resp.raise_for_status()
        for art in ET.fromstring(resp.text).findall("PubmedArticle"):
            yield parse_article(art)
        time.sleep(delay)

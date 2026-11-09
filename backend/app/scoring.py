"""Stage-1 scoring: a cheap, deterministic filter that decides which lenses a paper belongs to.

This is NOT the final ranker. Stage 2 (LLM scoring against the lens rubric) will add novelty, rigor
and accessibility. Until then only the `relevance` criterion is populated.
Any change here is a ranking change: run the evaluation harness (eval/) once it exists.
"""

import json
import math
import re
import sqlite3

from .db import now_iso
from .filters import FILTERS
from .lenses import load_lenses
from .models import LensConfig
from .sources import PaperRecord


def _keyword_pattern(kw: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(kw) + r"(?:s|es)?\b", re.I)


def keyword_score(lens: LensConfig, rec: PaperRecord) -> tuple[float, list[str]]:
    """Title hits count 2, abstract hits 1, each keyword once. Squashed to 0..1 (about 0.5 at 3 points)."""
    raw, matched = 0, []
    for kw in lens.keywords:
        pat = _keyword_pattern(kw)
        points = (2 if pat.search(rec.title) else 0) + (1 if pat.search(rec.abstract) else 0)
        if points:
            raw += points
            matched.append(kw)
    if not raw:
        # arXiv lenses ingested by category alone (useKeywords: false) get a small baseline.
        if rec.source == "arxiv" and lens.arxiv and not lens.arxiv.get("useKeywords", True):
            if set(lens.arxiv.get("categories", [])) & set(rec.categories):
                return 0.1, []
        return 0.0, []
    return round(1 - math.exp(-raw / 4), 3), matched


def score_for_lens(lens: LensConfig, rec: PaperRecord) -> tuple[float, str] | None:
    if rec.source not in lens.sources:
        return None
    if lens.filter:
        return FILTERS[lens.filter](rec)
    score, matched = keyword_score(lens, rec)
    if score <= 0:
        return None
    why = f"Matched lens keywords: {', '.join(matched)}." if matched else "In this lens's arXiv categories."
    return score, why


def assign_lenses(con: sqlite3.Connection, rec: PaperRecord) -> list[str]:
    """(Re)score a paper against every lens in the build and store the result."""
    assigned = []
    con.execute("DELETE FROM paper_lens WHERE paper_id = ?", (rec.id,))
    for lens in load_lenses():
        result = score_for_lens(lens, rec)
        if result is None:
            continue
        score, why = result
        con.execute(
            "INSERT INTO paper_lens (paper_id, lens_id, score, rubric, why, scored_at) VALUES (?,?,?,?,?,?)",
            (rec.id, lens.id, score, json.dumps({"relevance": score}), why, now_iso()))
        assigned.append(lens.id)
    return assigned


def record_from_row(row: sqlite3.Row) -> PaperRecord:
    return PaperRecord(
        id=row["id"], source=row["source"], external_id=row["external_id"], title=row["title"],
        abstract=row["abstract"], published=row["published"], authors=json.loads(row["authors"]),
        url=row["url"], doi=row["doi"], categories=json.loads(row["categories"]), extras=json.loads(row["extras"]))

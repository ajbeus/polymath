"""Builds API responses from the database. Everything here is real data; nothing is invented.

Stage-1 limits to keep in mind (see scoring.py): scores come from keyword rules and BM25, only the
`relevance` criterion is scored, summaries are the paper's own abstract text, and "why this matched"
reports the actual terms or rules that fired.
"""

import json
import math
import re
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone

from . import db
from .config import DIGEST_DAYS
from .lenses import get_lens, load_lenses
from .models import (AskResult, Cost, Digest, FeedbackEvent, Paper, PerLens, SinceLastVisit,
                     SourceStatus, SystemStatus)

SOURCES = ("arxiv", "pubmed", "biorxiv")
STOP = {"what", "the", "are", "and", "for", "about", "any", "how", "does", "with", "new", "recent",
        "latest", "paper", "papers", "on", "in", "of", "to", "is", "a", "an"}


def _summary(abstract: str, limit: int = 420) -> str:
    """The paper's own words: the first sentences of its abstract, cut at `limit` characters."""
    text = re.sub(r"\s+", " ", abstract).strip()
    if not text:
        return "No abstract available."
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > limit * 0.5 else cut.rsplit(" ", 1)[0] + "…"


def _paper(row: sqlite3.Row, lens_id: str, score: float, why: str, rubric: dict) -> Paper:
    return Paper(
        id=row["id"], lens_id=lens_id, title=row["title"], authors=json.loads(row["authors"]),
        source=row["source"], date=row["published"], score=score, summary=_summary(row["abstract"]),
        why_matched=why, rubric=rubric, url=row["url"], is_sample=False)


def lenses():
    return list(load_lenses())


def digest(lens_id: str) -> Digest | None:
    lens = get_lens(lens_id)
    if not lens:
        return None
    today = date.today()
    cutoff = (today - timedelta(days=DIGEST_DAYS)).isoformat()
    with db.connect() as con:
        rows = con.execute(
            "SELECT p.*, pl.score, pl.why, pl.rubric FROM paper_lens pl JOIN papers p ON p.id = pl.paper_id "
            "WHERE pl.lens_id = ? AND p.published >= ? ORDER BY pl.score DESC, p.published DESC LIMIT 40",
            (lens_id, cutoff)).fetchall()
        papers = [_paper(r, lens_id, r["score"], r["why"], json.loads(r["rubric"])) for r in rows]

        last_visit = db.get_meta(con, f"last_visit:{lens_id}")
        new_since = con.execute(
            "SELECT COUNT(*) FROM paper_lens pl JOIN papers p ON p.id = pl.paper_id "
            "WHERE pl.lens_id = ? AND p.ingested_at > ?", (lens_id, last_visit or "0")).fetchone()[0]
        db.set_meta(con, f"last_visit:{lens_id}", db.now_iso())

    if papers:
        by_source = {s: sum(1 for p in papers if p.source == s) for s in SOURCES}
        parts = ", ".join(f"{n} from {s}" for s, n in by_source.items() if n)
        summary = (f"{len(papers)} papers matched {lens.name} in the last {DIGEST_DAYS} days ({parts}). "
                   "Ranked by a keyword-based stage-1 score; rubric scoring by Claude is not connected yet.")
    else:
        summary = (f"No matching papers in the last {DIGEST_DAYS} days. "
                   f"Run `python -m app.ingest --lens {lens_id}` to pull some.")
    if last_visit:
        visit_text = f"{new_since} new matching papers were indexed since your last visit."
    else:
        visit_text = "First visit to this lens: nothing to compare against yet."

    monday = today - timedelta(days=today.weekday())
    return Digest(
        lens_id=lens_id, week_of=monday.isoformat(), generated_at=db.now_iso(), summary=summary,
        since_last_visit=SinceLastVisit(text=visit_text, new_papers=new_since if last_visit else 0, reranked=0),
        recommended=papers[:4], others=papers[4:], is_sample=False)


def _fts_query(question: str) -> tuple[str, list[str]]:
    toks = [t for t in re.findall(r"[a-z0-9]+", question.lower()) if len(t) > 2 and t not in STOP]
    return " OR ".join(f'"{t}"' for t in toks), toks


def ask(question: str, lens_id: str | None) -> AskResult:
    started = time.time()
    match, toks = _fts_query(question)
    results: list[Paper] = []
    if match:
        lens_filter = "AND pl.lens_id = ?" if lens_id else ""
        args = [match] + ([lens_id] if lens_id else [])
        with db.connect() as con:
            rows = con.execute(
                f"SELECT p.*, pl.lens_id AS lens_id, bm25(papers_fts, 0, 4.0, 1.0) AS rank "
                f"FROM papers_fts JOIN papers p ON p.id = papers_fts.id "
                f"JOIN paper_lens pl ON pl.paper_id = p.id "
                f"WHERE papers_fts MATCH ? {lens_filter} ORDER BY rank LIMIT 60", args).fetchall()
        seen = set()
        for r in rows:
            if r["id"] in seen:  # a paper in several lenses is listed once, under its best match
                continue
            seen.add(r["id"])
            strength = -r["rank"]  # bm25() is negative; larger magnitude = better match
            score = round(1 - math.exp(-strength / 6), 3)
            text = f"{r['title']} {r['abstract']}".lower()
            hit = [t for t in toks if t in text]
            why = f"Matched your terms in the title or abstract: {', '.join(hit)}." if hit else "Text match."
            results.append(_paper(r, r["lens_id"], score, why, {"relevance": score}))
            if len(results) == 5:
                break
    note = ("Stage-1 ranking: full-text BM25 over titles and abstracts in the local index. "
            "The Claude rubric scorer is not connected yet.")
    if not results:
        note = "No papers in the local index match those terms. Try other words, or run an ingest first."
    return AskResult(question=question, lens_id=lens_id, results=results,
                     took_ms=int((time.time() - started) * 1000), note=note, is_sample=False)


def links(lens_id: str, limit: int) -> list:
    """Cross-lens link discovery is not built yet; an empty list is the honest answer."""
    return []


def save_feedback(ev: FeedbackEvent) -> None:
    with db.connect() as con:
        con.execute("INSERT INTO feedback (paper_id, lens_id, action, active, at) VALUES (?,?,?,?,?)",
                    (ev.paper_id, ev.lens_id, ev.action, int(ev.active), ev.at))


def status() -> SystemStatus:
    since24 = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sources: list[SourceStatus] = []
    with db.connect() as con:
        for s in SOURCES:
            indexed = con.execute("SELECT COUNT(*) FROM papers WHERE source = ?", (s,)).fetchone()[0]
            added = con.execute("SELECT COUNT(*) FROM papers WHERE source = ? AND ingested_at > ?", (s, since24)).fetchone()[0]
            last = con.execute(
                "SELECT finished_at, error FROM ingest_runs WHERE source = ? AND finished_at IS NOT NULL "
                "ORDER BY id DESC LIMIT 1", (s,)).fetchone()
            if last is None:
                state = "delayed"  # never ingested
            elif last["error"]:
                state = "error"
            else:
                age = datetime.now(timezone.utc) - datetime.strptime(last["finished_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                state = "ok" if age < timedelta(hours=36) else "delayed"
            sources.append(SourceStatus(source=s, indexed=indexed, addedLast24h=added,
                                        last_ingest_at=last["finished_at"] if last else None, state=state))
        per_lens = [
            PerLens(lens_id=l.id, indexed=con.execute(
                "SELECT COUNT(*) FROM paper_lens WHERE lens_id = ?", (l.id,)).fetchone()[0])
            for l in load_lenses()]
        last_any = con.execute("SELECT MAX(finished_at) FROM ingest_runs WHERE error IS NULL").fetchone()[0]
    return SystemStatus(
        is_sample=False, last_ingest_at=last_any, next_ingest_at=None, sources=sources, per_lens=per_lens,
        evaluation=None, cost=Cost(budget_usd_per_day=0, days=[]))

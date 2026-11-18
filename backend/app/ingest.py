"""Ingest CLI. Run from backend/:

    python -m app.ingest --source arxiv                 # every arXiv lens in the build, last 14 days
    python -m app.ingest --source arxiv --lens fusion --days 30 --max 200
    python -m app.ingest --source pubmed --lens worm
    python -m app.ingest --source biorxiv               # scans all bioRxiv, keeps lens matches
    python -m app.ingest --rescore                      # re-score stored papers after editing a lens
"""

import argparse
import sys

import requests

from . import db, scoring
from .config import BUILD, DB_PATH
from .lenses import load_lenses
from .sources import arxiv, biorxiv, pubmed

FETCHERS = {"arxiv": arxiv.fetch, "pubmed": pubmed.fetch}
SOURCES = [*FETCHERS, "biorxiv"]


def ingest(source: str, lens, days: int, max_results: int) -> tuple[int, int]:
    """Fetch one lens's papers from one source, store them, and score them. Returns (fetched, new)."""
    with db.connect() as con:
        run_id = con.execute(
            "INSERT INTO ingest_runs (source, lens_id, started_at) VALUES (?,?,?)",
            (source, lens.id, db.now_iso())).lastrowid
    fetched = new = 0
    error = None
    try:
        with requests.Session() as session, db.connect() as con:
            for rec in FETCHERS[source](lens, days, max_results, session):
                fetched += 1
                new += db.upsert_paper(con, rec)
                scoring.assign_lenses(con, rec)
                if fetched % 50 == 0:
                    con.commit()
    except Exception as e:  # keep going with other lenses; the failure is recorded for the status page
        error = f"{type(e).__name__}: {e}"
    with db.connect() as con:
        con.execute("UPDATE ingest_runs SET finished_at=?, fetched=?, new=?, error=? WHERE id=?",
                    (db.now_iso(), fetched, new, error, run_id))
    if error:
        print(f"  ERROR {error}")
    return fetched, new


def ingest_biorxiv(lenses, days: int, max_results: int) -> dict[str, tuple[int, int]]:
    """bioRxiv has no search, so scan every preprint in the window once and store only those that match
    at least one of `lenses`. Returns {lens_id: (matched, new)}; `max_results` caps papers stored per lens."""
    runs = {}
    with db.connect() as con:
        for lens in lenses:
            runs[lens.id] = con.execute(
                "INSERT INTO ingest_runs (source, lens_id, started_at) VALUES (?,?,?)",
                ("biorxiv", lens.id, db.now_iso())).lastrowid
    counts = {l.id: [0, 0] for l in lenses}
    scanned = 0
    error = None
    try:
        with requests.Session() as session, db.connect() as con:
            for rec in biorxiv.fetch(days, session):
                scanned += 1
                hits = [l for l in lenses if counts[l.id][0] < max_results and scoring.score_for_lens(l, rec)]
                if not hits:
                    continue
                is_new = db.upsert_paper(con, rec)
                scoring.assign_lenses(con, rec)
                for l in hits:
                    counts[l.id][0] += 1
                    counts[l.id][1] += is_new
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    with db.connect() as con:
        for lens in lenses:
            con.execute("UPDATE ingest_runs SET finished_at=?, fetched=?, new=?, error=? WHERE id=?",
                        (db.now_iso(), counts[lens.id][0], counts[lens.id][1], error, runs[lens.id]))
    if error:
        print(f"  ERROR {error}")
    print(f"  scanned {scanned} bioRxiv preprints")
    return {k: (v[0], v[1]) for k, v in counts.items()}


def rescore() -> int:
    with db.connect() as con:
        rows = con.execute("SELECT * FROM papers").fetchall()
        for row in rows:
            scoring.assign_lenses(con, scoring.record_from_row(row))
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=[*SOURCES, "all"], default="all")
    ap.add_argument("--lens", help="lens id (default: every lens in the build)")
    ap.add_argument("--days", type=int, default=14, help="how far back to look")
    ap.add_argument("--max", type=int, default=200, help="max papers per lens and source")
    ap.add_argument("--rescore", action="store_true", help="re-score stored papers, no network")
    args = ap.parse_args()

    db.init_db()
    print(f"build={BUILD} db={DB_PATH}")
    if args.rescore:
        print(f"rescored {rescore()} papers")
        return 0

    lenses = [l for l in load_lenses() if not args.lens or l.id == args.lens]
    if not lenses:
        print(f"no such lens in this build: {args.lens}")
        return 1
    sources = SOURCES if args.source == "all" else [args.source]
    if "biorxiv" in sources:
        bio = [l for l in lenses if "biorxiv" in l.sources]
        if bio:
            print(f"[{', '.join(l.id for l in bio)}/biorxiv] last {args.days} days, scanning everything posted ...")
            for lid, (matched, new) in ingest_biorxiv(bio, args.days, args.max).items():
                print(f"  {lid}: matched {matched}, new {new}")
    for lens in lenses:
        for source in sources:
            if source == "biorxiv":
                continue
            if source not in lens.sources:
                continue
            cfg = lens.arxiv if source == "arxiv" else lens.pubmed
            if not cfg:
                print(f"[{lens.id}/{source}] no ingest settings in lens config, skipping")
                continue
            print(f"[{lens.id}/{source}] last {args.days} days, up to {args.max} papers ...")
            fetched, new = ingest(source, lens, args.days, args.max)
            print(f"  fetched {fetched}, new {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

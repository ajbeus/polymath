"""Build (or extend) the labeling pool for a lens.

    python eval/build_pool.py worm            # run with backend/.venv/Scripts/python

The pool mixes papers the filter KEPT and papers it REJECTED, so labels can measure both precision
(did we surface junk?) and recall (did we hide good papers?). Sampling is seeded and existing labels
are never overwritten: re-running only adds new papers.
"""

import random
import sys

from common import get_lens, lens_pool_path, db, rank_score, read_pool, write_pool

KEPT, REJECTED = 70, 50  # sample sizes; raise them to grow the labeled set


def main(lens_id: str) -> None:
    lens = get_lens(lens_id)
    if lens is None:
        sys.exit(f"unknown lens {lens_id}")
    sources = tuple(lens.sources)
    with db.connect() as con:
        marks = ",".join("?" * len(sources))
        papers = con.execute(
            f"SELECT id, title, abstract FROM papers WHERE source IN ({marks}) ORDER BY id", sources).fetchall()

    existing = {r["id"]: r for r in read_pool(lens_id)}
    scored = {p["id"]: rank_score(lens_id, p["id"]) for p in papers}
    kept = [p for p in papers if scored[p["id"]] is not None and p["id"] not in existing]
    rejected = [p for p in papers if scored[p["id"]] is None and p["id"] not in existing]

    rng = random.Random(455)
    have_kept = sum(1 for r in existing.values() if r["filter_decision"] == "kept")
    have_rej = len(existing) - have_kept
    add = rng.sample(kept, min(len(kept), max(0, KEPT - have_kept))) + \
          rng.sample(rejected, min(len(rejected), max(0, REJECTED - have_rej)))

    rows = list(existing.values())
    for p in add:
        s = scored[p["id"]]
        rows.append({"id": p["id"], "title": p["title"], "abstract": p["abstract"],
                     "filter_decision": "rejected" if s is None else "kept",
                     "filter_score": "" if s is None else s, "claude_guess": "", "label": "", "notes": ""})
    # Refresh decisions/scores for existing rows (the filter may have changed); keep labels.
    for r in rows:
        s = scored.get(r["id"])
        r["filter_decision"] = "rejected" if s is None else "kept"
        r["filter_score"] = "" if s is None else s
    write_pool(lens_id, rows)
    print(f"{lens_pool_path(lens_id)}: {len(rows)} papers ({len(add)} added)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "worm")

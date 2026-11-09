"""Shared helpers for the evaluation scripts. Imports the real backend code so the harness
measures exactly what the API serves."""

import csv
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import db, scoring  # noqa: E402
from app.lenses import get_lens  # noqa: E402

POOL_FIELDS = ["id", "title", "abstract", "filter_decision", "filter_score", "claude_guess", "label", "notes"]


def lens_pool_path(lens_id: str) -> Path:
    return EVAL_DIR / lens_id / "pool.csv"


def read_pool(lens_id: str) -> list[dict]:
    path = lens_pool_path(lens_id)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_pool(lens_id: str, rows: list[dict]) -> None:
    path = lens_pool_path(lens_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel reads UTF-8
        w = csv.DictWriter(f, fieldnames=POOL_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_record(paper_id: str):
    with db.connect() as con:
        row = con.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    return scoring.record_from_row(row) if row else None


def rank_score(lens_id: str, paper_id: str) -> float | None:
    """Score the production ranker gives this paper for the lens; None if the filter rejects it."""
    rec = load_record(paper_id)
    if rec is None:
        return None
    result = scoring.score_for_lens(get_lens(lens_id), rec)
    return None if result is None else result[0]

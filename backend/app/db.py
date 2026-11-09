"""SQLite store. One file, no server. Raw source records are kept untouched alongside parsed rows."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,              -- 'arxiv:2511.01234', 'pubmed:12345678'
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '[]',     -- JSON list
    abstract TEXT NOT NULL DEFAULT '',
    published TEXT NOT NULL,                -- YYYY-MM-DD
    url TEXT,
    doi TEXT,
    categories TEXT NOT NULL DEFAULT '[]',  -- JSON list (arXiv categories, PubMed MeSH)
    extras TEXT NOT NULL DEFAULT '{}',      -- JSON, source-specific fields for lens filters
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS papers_published ON papers(published);

CREATE TABLE IF NOT EXISTS raw_records (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id),
    format TEXT NOT NULL,
    body TEXT NOT NULL
);

-- Stage-1 score of a paper against one lens. Stage 2 (LLM rubric scoring) will fill `rubric` further.
CREATE TABLE IF NOT EXISTS paper_lens (
    paper_id TEXT NOT NULL REFERENCES papers(id),
    lens_id TEXT NOT NULL,
    score REAL NOT NULL,
    rubric TEXT NOT NULL DEFAULT '{}',
    why TEXT NOT NULL DEFAULT '',
    scored_at TEXT NOT NULL,
    PRIMARY KEY (paper_id, lens_id)
);
CREATE INDEX IF NOT EXISTS paper_lens_lens ON paper_lens(lens_id, score DESC);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL,
    lens_id TEXT NOT NULL,
    action TEXT NOT NULL,
    active INTEGER NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    lens_id TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    fetched INTEGER DEFAULT 0,
    new INTEGER DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    id UNINDEXED, title, abstract, tokenize = 'porter unicode61'
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_paper(con: sqlite3.Connection, rec) -> bool:
    """Insert or refresh a paper and its raw record. Returns True if the paper was new."""
    existed = con.execute("SELECT 1 FROM papers WHERE id = ?", (rec.id,)).fetchone() is not None
    values = (
        rec.id, rec.source, rec.external_id, rec.title, json.dumps(rec.authors), rec.abstract,
        rec.published, rec.url, rec.doi, json.dumps(rec.categories), json.dumps(rec.extras), now_iso(),
    )
    if existed:
        con.execute(
            "UPDATE papers SET title=?, authors=?, abstract=?, published=?, url=?, doi=?, categories=?, extras=? WHERE id=?",
            (rec.title, json.dumps(rec.authors), rec.abstract, rec.published, rec.url, rec.doi,
             json.dumps(rec.categories), json.dumps(rec.extras), rec.id),
        )
        con.execute("DELETE FROM papers_fts WHERE id = ?", (rec.id,))
    else:
        con.execute(
            "INSERT INTO papers (id, source, external_id, title, authors, abstract, published, url, doi, categories, extras, ingested_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", values)
    con.execute("INSERT INTO papers_fts (id, title, abstract) VALUES (?,?,?)", (rec.id, rec.title, rec.abstract))
    con.execute(
        "INSERT OR REPLACE INTO raw_records (paper_id, format, body) VALUES (?,?,?)",
        (rec.id, rec.raw_format, rec.raw_body))
    return not existed


def get_meta(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))

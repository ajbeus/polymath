"""Abstract fetcher + relevance filter for the WormLab VOC project.

Pipeline position: takes the PMIDs found by the link hopper, fetches their
records from PubMed (efetch), saves the raw XML untouched, parses out the
fields we care about, flags which papers look relevant to C. elegans odor
responses, and writes everything to SQLite + CSV.

Abstracts are only a FILTER. They nominate papers and compounds; the real
labels (compound, concentration, attract/repel) come from full text later.

Usage:
    # fetch from NCBI (set NCBI_API_KEY in your environment, never in code)
    python abstract_parser.py --pmids pmids.json

    # re-parse XML you already downloaded (no network needed)
    python abstract_parser.py --reparse

    # remove off-topic abstracts from the pipeline JSON file
    python abstract_parser.py --filter-json

pmids.json can be either a list of PMIDs, or a PMID-keyed dict such as
pipeline/papers_data/abstracts.json ({pmid: {"depth": ..., "found_from": ...}}).
Output goes to parser/data unless --data-dir says otherwise.
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
 
import requests
 
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH_SIZE = 100  # PMIDs per efetch request
 
# --- relevance terms (regex stems, case-insensitive) ---------------------
# Strong organism terms. "nematode" alone is weaker (many worm species).
WORM_STRONG = re.compile(r"\b(c\.\s?elegans|caenorhabditis)\b", re.I)
WORM_WEAK = re.compile(r"\bnematodes?\b|\bworms?\b", re.I)
 
# Chemosensation / odor-response terms.
CHEMO = re.compile(
    r"\b(chemotax\w*|chemosens\w*|chemoattract\w*|chemorepel\w*|olfact\w*|"
    r"odou?r\w*|volatile\w*|attract\w*|repel\w*|repuls\w*|avoid\w*|aversi\w*)",
    re.I,
)
# Words that signal a direction of response, used for hint sentences.
DIRECTION = re.compile(
    r"\b(attract\w*|repel\w*|repuls\w*|avoid\w*|aversi\w*|chemoattract\w*|"
    r"chemorepel\w*|neutral)\b",
    re.I,
)
# MeSH headings that strongly suggest on-topic papers.
GOOD_MESH = {"Chemotaxis", "Olfactory Perception", "Smell", "Odorants",
             "Olfactory Receptor Neurons", "Chemoreceptor Cells"}
 
# --- tiered odor score -----------------------------------------------------
# Each family counts ONCE per paper ("odor, odors, odorants" is one hit), so
# long abstracts can't pile up points. Weights favour words that point at
# volatile odor responses. Salt/taste chemotaxis is real chemotaxis but not
# volatile, so it is penalised; aging/disease papers often use chemotaxis
# only as a behavioural readout, so they get a small penalty.
# These weights are a starting point -- tune them against hand review.
SCORE_FAMILIES = {
    "odor":       (3, re.compile(r"\b(odou?r\w*|smell\w*)", re.I)),
    "volatile":   (3, re.compile(r"\b(volatile\w*|VOCs?)\b", re.I)),
    "olfactory":  (2, re.compile(r"\bolfact\w*", re.I)),
    "chemotaxis": (2, re.compile(r"\b(chemotax\w*|chemosens\w*|chemoattract\w*|chemorepel\w*)", re.I)),
    "attract":    (2, re.compile(r"\b(attract\w*|repel\w*|repuls\w*)", re.I)),
    "avoid":      (1, re.compile(r"\b(avoid\w*|aversi\w*)", re.I)),
}
PENALTY_FAMILIES = {
    "salt_taste":    (3, re.compile(r"\b(salts?|nacl|sodium chloride|gustat\w*|taste\w*)\b", re.I)),
    "aging_disease": (1, re.compile(r"\b(lifespan|life span|longevity|neurodegenerat\w*|amyloid|parkinson\w*|alzheimer\w*)\b", re.I)),
}
MESH_BONUS = 2   # per good MeSH heading, capped at 2 headings
RELEVANT_MIN = 5  # score needed (with C. elegans named) to be "relevant"
MAYBE_MIN = 2     # score needed to be "maybe"
 
 
def text_of(el):
    """All text inside an element, including nested markup (<i>, <sub>...)."""
    return "".join(el.itertext()).strip() if el is not None else ""
 
 
def parse_article(art):
    """Turn one <PubmedArticle> element into a flat dict."""
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
    year = text_of(article.find("Journal/JournalIssue/PubDate/Year"))
    if not year:  # older records use <MedlineDate>1993 Feb</MedlineDate>
        m = re.search(r"\d{4}", text_of(article.find("Journal/JournalIssue/PubDate/MedlineDate")))
        year = m.group(0) if m else ""
 
    mesh = [text_of(d) for d in cit.findall("MeshHeadingList/MeshHeading/DescriptorName")]
 
    doi = pmcid = ""
    for aid in art.findall("PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi":
            doi = text_of(aid)
        elif aid.get("IdType") == "pmc":
            pmcid = text_of(aid)
 
    return {"pmid": pmid, "title": title, "abstract": abstract, "journal": journal,
            "year": year, "mesh": mesh, "doi": doi, "pmcid": pmcid}
 
 
def split_sentences(text):
    """Cheap sentence splitter; good enough for abstracts."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if s.strip()]
 
 
def odor_score(blob, good_mesh):
    """Weighted odor-relevance score plus a readable breakdown, e.g.
    'odor+3;olfactory+2;salt_taste-3'. Sort by this when reviewing by hand."""
    score, parts = 0, []
    for name, (weight, rx) in SCORE_FAMILIES.items():
        if rx.search(blob):
            score += weight
            parts.append(f"{name}+{weight}")
    for name, (weight, rx) in PENALTY_FAMILIES.items():
        if rx.search(blob):
            score -= weight
            parts.append(f"{name}-{weight}")
    bonus = MESH_BONUS * min(len(good_mesh), 2)
    if bonus:
        score += bonus
        parts.append(f"mesh+{bonus}")
    return score, ";".join(parts)
 
 
def score_relevance(rec):
    """Add relevance fields to a parsed record.
 
    relevant : names C. elegans AND odor_score >= RELEVANT_MIN
    maybe    : a worm named and odor_score >= MAYBE_MIN, OR strong odor
               language with no worm named, OR a worm paper with no abstract
               (title-only, so we can't judge it -- look at it by hand)
    off_topic: everything else
    """
    blob = f"{rec['title']} {rec['abstract']}"
    worm_strong = bool(WORM_STRONG.search(blob)) or any(
        "Caenorhabditis elegans" in m for m in rec["mesh"])
    worm_weak = bool(WORM_WEAK.search(blob))
    has_worm = worm_strong or worm_weak
    chemo_terms = sorted({m.group(0).lower() for m in CHEMO.finditer(blob)})
    good_mesh = sorted(set(rec["mesh"]) & GOOD_MESH)
    score, detail = odor_score(blob, good_mesh)
 
    if worm_strong and score >= RELEVANT_MIN:
        label = "relevant"
    elif has_worm and score >= MAYBE_MIN:
        label = "maybe"
    elif score >= RELEVANT_MIN:  # strong odor language, no worm named
        label = "maybe"
    else:
        label = "off_topic"
    if not rec["abstract"] and has_worm and label == "off_topic":
        label = "maybe"
 
    # Provisional hints: sentences with direction language. Abstract-level
    # evidence only -- these still need confirming in the full text.
    hints = [s for s in split_sentences(rec["abstract"]) if DIRECTION.search(s)]
 
    rec.update({
        "relevance": label,
        "worm_match": "strong" if worm_strong else ("weak" if worm_weak else "none"),
        "odor_score": score,
        "score_detail": detail,
        "chemo_terms": ";".join(chemo_terms),
        "good_mesh": ";".join(good_mesh),
        "hint_sentences": " || ".join(hints),
        "has_abstract": bool(rec["abstract"]),
    })
    return rec


def write_json_atomic(path, data):
    """Write JSON via a temp file + rename so readers never see a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as output:
            temp_path = Path(output.name)
            json.dump(data, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def filter_abstracts_json(path):
    """Remove off-topic records and rate the retained abstracts in a JSON file."""
    path = Path(path)
    with path.open(encoding="utf-8") as source:
        papers = json.load(source)
    if not isinstance(papers, dict):
        raise ValueError(f"Expected a PMID-keyed JSON object in {path}")

    retained = {}
    for pmid, paper in papers.items():
        if not isinstance(paper, dict):
            raise ValueError(f"Expected an object for PMID {pmid} in {path}")
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        keywords = paper.get("keywords", [])
        if not isinstance(title, str) or not isinstance(abstract, str):
            raise ValueError(f"Expected title and abstract strings for PMID {pmid}")
        if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
            raise ValueError(f"Expected a list of keyword strings for PMID {pmid}")

        record = score_relevance({"title": title, "abstract": abstract, "mesh": keywords})
        if record["relevance"] != "off_topic":
            paper["relevance"] = record["relevance"]
            retained[pmid] = paper

    write_json_atomic(path, retained)
    removed = len(papers) - len(retained)
    print(f"Removed {removed} off-topic abstracts; kept {len(retained)} relevant or maybe abstracts in {path}")


def fetch_batch(pmids, api_key=None):
    """efetch one batch of PMIDs; returns the raw XML text."""
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    if api_key:
        params["api_key"] = api_key
    r = requests.post(EFETCH_URL, data=params, timeout=60)  # POST: long id lists
    r.raise_for_status()
    return r.text
 
 
def fetch_all(pmids, raw_dir, api_key=None):
    """Fetch every PMID not already on disk. Raw XML is saved one file per
    paper and never edited, so parsing can be re-run without the API."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    todo = [p for p in pmids if not (raw_dir / f"{p}.xml").exists()]
    delay = 0.11 if api_key else 0.35  # stay under 10/s with key, 3/s without
    print(f"{len(pmids)} PMIDs, {len(todo)} to fetch")
    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i:i + BATCH_SIZE]
        root = ET.fromstring(fetch_batch(batch, api_key))
        for art in root.findall("PubmedArticle"):
            pmid = text_of(art.find("MedlineCitation/PMID"))
            (raw_dir / f"{pmid}.xml").write_text(
                ET.tostring(art, encoding="unicode"), encoding="utf-8")
        print(f"  fetched {min(i + BATCH_SIZE, len(todo))}/{len(todo)}")
        time.sleep(delay)
 
 
SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    pmid TEXT PRIMARY KEY,
    pmcid TEXT, doi TEXT, title TEXT, abstract TEXT, journal TEXT, year TEXT,
    mesh TEXT, relevance TEXT, worm_match TEXT, odor_score INTEGER,
    score_detail TEXT, chemo_terms TEXT,
    good_mesh TEXT, hint_sentences TEXT, has_abstract INTEGER,
    depth INTEGER, found_from TEXT,
    raw_path TEXT,
    status TEXT DEFAULT 'abstract_parsed'
);
"""
 
 
def write_outputs(records, db_path, csv_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute(SCHEMA)
    # databases made by an older version of this script lack the new columns
    have = {row[1] for row in con.execute("PRAGMA table_info(papers)")}
    for col, typ in (("odor_score", "INTEGER"), ("score_detail", "TEXT")):
        if col not in have:
            con.execute(f"ALTER TABLE papers ADD COLUMN {col} {typ}")
    cols = ["pmid", "pmcid", "doi", "title", "abstract", "journal", "year", "mesh",
            "relevance", "worm_match", "odor_score", "score_detail", "chemo_terms", "good_mesh", "hint_sentences",
            "has_abstract", "depth", "found_from", "raw_path"]
    for r in records:
        r = dict(r, mesh=";".join(r["mesh"]))
        con.execute(
            f"INSERT OR REPLACE INTO papers ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [r.get(c) for c in cols])
    con.commit()
    con.close()
 
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols[:1] + ["pubmed_link"] + cols[1:])
        for r in records:
            r = dict(r, mesh=";".join(r["mesh"]))
            w.writerow([r["pmid"], f"https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/"]
                       + [r.get(c) for c in cols[1:]])
 
 
def load_pmids(path):
    """Accepts a list of PMIDs or Xana's {pmid: {depth, found_from}} dict."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [str(k) for k in data], data
    return [str(p) for p in data], {}
 
 
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pmids", help="JSON file: list of PMIDs or the link-hopper dict")
    ap.add_argument("--data-dir", default=str(Path(__file__).resolve().parent / "data"))
    ap.add_argument("--reparse", action="store_true", help="skip fetching; parse XML already in <data-dir>/raw")
    ap.add_argument(
        "--filter-json",
        action="store_true",
        help="remove off-topic records from pipeline/papers_data/abstracts.json",
    )
    ap.add_argument(
        "--json-file",
        default=str(Path(__file__).resolve().parent.parent / "pipeline" / "papers_data" / "abstracts.json"),
        help="JSON file to filter with --filter-json",
    )
    args = ap.parse_args()

    if args.filter_json:
        filter_abstracts_json(args.json_file)
        return

    data_dir = Path(args.data_dir)
    raw_dir = data_dir / "raw" / "pubmed_xml"
    meta = {}
 
    if args.pmids:
        pmids, meta = load_pmids(args.pmids)
    else:
        pmids = [p.stem for p in raw_dir.glob("*.xml")]
 
    if not args.reparse:
        if not args.pmids:
            ap.error("give --pmids, or use --reparse")
        # PUBMED_API_KEY is still accepted for older setups.
        fetch_all(pmids, raw_dir, os.environ.get("NCBI_API_KEY") or os.environ.get("PUBMED_API_KEY"))
 
    records = []
    for pmid in pmids:
        path = raw_dir / f"{pmid}.xml"
        if not path.exists():
            print(f"  missing raw XML for {pmid}, skipping")
            continue
        rec = score_relevance(parse_article(ET.parse(path).getroot()))
        rec["raw_path"] = str(path)
        rec["depth"] = meta.get(pmid, {}).get("depth")
        rec["found_from"] = meta.get(pmid, {}).get("found_from")
        records.append(rec)
 
    write_outputs(records, data_dir / "db" / "worm_voc.sqlite", data_dir / "papers.csv")
    counts = {}
    for r in records:
        counts[r["relevance"]] = counts.get(r["relevance"], 0) + 1
    print(f"parsed {len(records)} papers: {counts}")
    print(f"wrote {data_dir / 'db' / 'worm_voc.sqlite'} and {data_dir / 'papers.csv'}")
 
 
if __name__ == "__main__":
    main()
 
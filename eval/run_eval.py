"""Evaluation harness. Run it after ANY ranking change (scoring rules, lens keywords/filters, weights).

    backend/.venv/Scripts/python eval/run_eval.py worm
    backend/.venv/Scripts/python eval/run_eval.py worm --use-guesses   # fall back to Claude's provisional labels

It scores every labeled paper with the production ranker (app.scoring.score_for_lens), ranks them,
and reports precision@k, nDCG@k, filter recall, and a structural citation check. Results are saved to
eval/results/ and compared with the previous run of the same lens.

Labels: 2 = relevant, 1 = maybe/related, 0 = not relevant (see eval/README.md).
Caveat: precision@k here is computed inside the labeled pool (a sample), not over all of PubMed, so
use it to compare versions of the ranker, not as an absolute quality number.
"""

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone

from common import EVAL_DIR, db, rank_score, read_pool

KS = (5, 10)


def dcg(gains: list[int]) -> float:
    return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked_labels: list[int], all_labels: list[int], k: int) -> float:
    ideal = dcg(sorted(all_labels, reverse=True)[:k])
    return dcg(ranked_labels[:k]) / ideal if ideal else 0.0


def citation_ok(paper_id: str) -> bool:
    """Structural check: the id is in the index with the URL its source format implies.
    It does not call PubMed/arXiv, so it cannot catch a paper that was later retracted or deleted."""
    with db.connect() as con:
        row = con.execute("SELECT source, external_id, url FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not row:
        return False
    if row["source"] == "pubmed":
        return bool(re.fullmatch(r"\d+", row["external_id"])) and row["url"] == f"https://pubmed.ncbi.nlm.nih.gov/{row['external_id']}/"
    if row["source"] == "arxiv":
        return row["url"] == f"https://arxiv.org/abs/{row['external_id']}"
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lens")
    ap.add_argument("--use-guesses", action="store_true", help="use claude_guess where label is blank")
    args = ap.parse_args()

    rows = read_pool(args.lens)
    labeled = []
    n_human = n_guess = 0
    for r in rows:
        label, source = r["label"].strip(), "human"
        if label == "" and args.use_guesses and r["claude_guess"].strip():
            label, source = r["claude_guess"].strip(), "guess"
        if label not in ("0", "1", "2"):
            continue
        n_human += source == "human"
        n_guess += source == "guess"
        labeled.append({"id": r["id"], "title": r["title"], "label": int(label), "score": rank_score(args.lens, r["id"])})
    if not labeled:
        print(f"No labels in eval/{args.lens}/pool.csv. Fill the `label` column (0/1/2), or pass --use-guesses.")
        return 1

    kept = sorted((p for p in labeled if p["score"] is not None), key=lambda p: -p["score"])
    rejected = [p for p in labeled if p["score"] is None]
    all_labels = [p["label"] for p in labeled]
    ranked_labels = [p["label"] for p in kept]

    metrics: dict = {}
    for k in KS:
        top = ranked_labels[:k]
        metrics[f"precision@{k}_strict"] = sum(l == 2 for l in top) / k    # relevant only
        metrics[f"precision@{k}_lenient"] = sum(l >= 1 for l in top) / k   # relevant or related
        metrics[f"ndcg@{k}"] = ndcg_at_k(ranked_labels, all_labels, k)
    rel_total = sum(l == 2 for l in all_labels)
    any_total = sum(l >= 1 for l in all_labels)
    metrics["filter_recall_strict"] = sum(p["label"] == 2 for p in kept) / rel_total if rel_total else None
    metrics["filter_recall_lenient"] = sum(p["label"] >= 1 for p in kept) / any_total if any_total else None
    metrics["kept_precision_lenient"] = sum(p["label"] >= 1 for p in kept) / len(kept) if kept else None
    top10 = kept[:10]
    metrics["citation_validity_top10"] = sum(citation_ok(p["id"]) for p in top10) / len(top10) if top10 else None

    result = {
        "lens": args.lens, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "labels": {"human": n_human, "claude_guess": n_guess, "relevant": rel_total, "related": any_total - rel_total,
                   "total": len(labeled)},
        "metrics": metrics,
        "false_positives": [p["title"] for p in kept if p["label"] == 0][:8],
        "missed": [p["title"] for p in rejected if p["label"] >= 1],
    }

    out_dir = EVAL_DIR / "results"
    out_dir.mkdir(exist_ok=True)
    previous = sorted(out_dir.glob(f"{args.lens}-*.json"))
    prev = json.loads(previous[-1].read_text(encoding="utf-8")) if previous else None
    (out_dir / f"{args.lens}-{result['at'].replace(':', '')}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    src = f"{n_human} human" + (f" + {n_guess} Claude-guessed" if n_guess else "")
    print(f"lens={args.lens}  labeled papers: {len(labeled)} ({src})  relevant={rel_total} related={any_total - rel_total}")
    if n_guess:
        print("WARNING: includes unreviewed Claude guesses. Treat as a smoke test, not a measurement.")
    if prev and (prev["labels"]["human"], prev["labels"]["claude_guess"]) != (n_human, n_guess):
        prev = None  # label set changed; deltas would be meaningless
    for name, v in metrics.items():
        if v is None:
            print(f"  {name:28s} n/a")
            continue
        pv = (prev or {}).get("metrics", {}).get(name)
        delta = f"  ({v - pv:+.3f} vs previous)" if pv is not None else ""
        print(f"  {name:28s} {v:.3f}{delta}")
    print(f"\nkept {len(kept)}, rejected {len(rejected)}")
    if result["false_positives"]:
        print("Kept but labeled not relevant:")
        for t in result["false_positives"]:
            print("   -", t[:100])
    if result["missed"]:
        print("Rejected but labeled relevant/related:")
        for t in result["missed"]:
            print("   -", t[:100])
    return 0


if __name__ == "__main__":
    sys.exit(main())

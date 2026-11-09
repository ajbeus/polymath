# Evaluation

Measures how well the production ranker (the same code the API uses) surfaces papers you would
actually want. **Run it after any ranking change.**

```
backend/.venv/Scripts/python eval/run_eval.py worm
```
(Run from the repo root or from `eval/`. Add `--use-guesses` for a smoke test with Claude's unreviewed labels.)

## Labeling (the part only you can do)
Open `eval/worm/pool.csv` in a spreadsheet (UTF-8; Excel opens it correctly). For each row, read the
title and abstract and fill the **`label`** column:

| label | meaning for the worm lab |
|---|---|
| 2 | Relevant: C. elegans odor/volatile/olfactory/chemosensory behavior or neurons, odorant chemistry with worms, chemotaxis assay methods |
| 1 | Related: C. elegans sensory behavior or memory where odor is probably not the focus, pheromone biochemistry, VOC exposure effects |
| 0 | Not relevant (other nematodes, toxicology, aging, imaging tools, etc.) |

`claude_guess` is Claude's first-pass label, provided to save you time. The harness **ignores it**
unless you pass `--use-guesses`. Rows with a note ("Claude unsure") are the ones to check first. Please
confirm or overwrite every row in `label`; guessed labels are not a measurement.

The pool is 120 papers: 70 the filter kept and 50 it rejected, so both false alarms and misses show up.
Grow it with `python eval/build_pool.py worm` after raising `KEPT`/`REJECTED` (existing labels are preserved).

## What the numbers mean
- **precision@k (strict / lenient):** share of the top k ranked papers labeled 2 (strict) or 1-2 (lenient).
- **nDCG@k:** like precision but rewards putting 2s above 1s and near the top. 1.0 is perfect.
- **filter_recall:** share of your relevant papers that the filter kept at all. A paper it rejects can never be recommended.
- **kept_precision_lenient:** share of kept papers that are at least related.
- **citation_validity_top10:** structural only: every returned id is in the index with the URL its source format implies. It does not re-query PubMed/arXiv.

Limits: the pool is a sample (the rejected side is under-sampled, so recall is optimistic), and metrics are
computed inside the pool, not over all of PubMed. Use them to compare versions of the ranker, not as an absolute score.
Not built yet: per-question (Ask) evaluation and coverage versus a general chatbot, which need labeled queries and chatbot answers.

Results are saved in `eval/results/` (git-ignored), and each run prints the change versus the previous run on the same labels.

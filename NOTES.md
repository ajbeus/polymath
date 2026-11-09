# NOTES

Handoff notes for Polymath (CSE 455). Keep this short and current. Last updated 2026-11-09.

## Architecture
- `frontend/`: React + TS + Vite + Tailwind v4. Talks only to `src/api/index.ts` (`PolymathApi`). If `VITE_API_URL` is set it uses `src/api/http.ts` (real backend, no sample badges); otherwise `src/api/mock.ts` (JSON fixtures, fake delay, "Sample data" badges everywhere). Mock mode is the safe demo default.
- `backend/`: FastAPI + SQLite (FTS5). Same six endpoints as `PolymathApi`: `/lenses`, `/lenses/{id}/digest`, `/ask`, `/feedback`, `/links`, `/status`. JSON is camelCase, mirroring `frontend/src/types.ts`.
  - `app/sources/` arxiv.py, pubmed.py (fetch + parse), `app/filters/worm_voc.py` (lens-specific scorer), `app/scoring.py` (stage-1 lens assignment), `app/ingest.py` (CLI), `app/service.py` (response building).
- `lenses/{showcase,full}/<id>.json`: lens configs (shared). Backend-only fields: `arxiv`, `pubmed`, `filter`.
- `frontend/src/api/fixtures/{showcase,full}/`: mock data per lens. `eval/`: empty (harness not built).
- `abstract_parser.py` (repo root): original worm parser, untouched. Its logic was ported into the backend; safe to delete.
- Details and commands also in `CLAUDE.md`.

## Decisions
- One flag, `VITE_BUILD` (`showcase` default, or `full`), in the root `.env`; it controls both front end and backend. Showcase = worm, fusion, math, with no full-only data bundled.
- App name and assistant name (default "Ada") are env config, never hardcoded.
- Placeholder papers are obviously fake (`SAMPLE-` ids, no URLs). Real data never invents citations.
- Backend stage 1 = keyword rules + BM25. Only the `relevance` criterion is scored; other rubric criteria are absent, not faked. Summaries are the paper's own abstract text.
- Worm lens: C. elegans must be named (plant-parasitic nematode papers are rejected). Parser weights are otherwise unchanged apart from two bug fixes: `chemota[cx]` stem and excluding "volatile anesthetic".
- API port is 8765 (8000 was already in use on this machine).

## How to run
Front end (from `frontend/`; copy `.env.example` to root `.env` first):
```
npm install
npm run dev:showcase      # or dev:full
npm run dev:live          # against the real backend at http://127.0.0.1:8765 (start the backend first)
npm run build:showcase    # typecheck + build; also build:full
```
Backend (from `backend/`, Windows paths; venv already created):
```
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m app.ingest --source arxiv --days 14 --max 200
.venv/Scripts/python -m app.ingest --source pubmed --lens worm --days 60
.venv/Scripts/python -m app.ingest --rescore       # after editing lens keywords or filters
.venv/Scripts/python -m uvicorn app.main:app --port 8765
```
Eval (from repo root): `backend/.venv/Scripts/python eval/run_eval.py worm` (add `--use-guesses` for unlabeled smoke test); `eval/build_pool.py worm` grows the pool.
DB lives at `backend/data/polymath.sqlite` (git-ignored). Optional env: `NCBI_API_KEY`, `CONTACT_EMAIL`, `DIGEST_DAYS`, `POLYMATH_DB`.

## What's left
1. **Eval set: harness built, labels need the user.** `eval/worm/pool.csv` has 120 papers (70 kept + 50 rejected by the worm filter). The `claude_guess` column is Claude's unreviewed first pass (31 relevant, 19 related, 70 not). User must fill the `label` column (0/1/2; see `eval/README.md`; check rows with a "Claude unsure" note first). Run `backend/.venv/Scripts/python eval/run_eval.py worm` after any ranking change. Smoke-test result with guesses: P@10 strict 0.80, nDCG@10 0.86, filter recall 0.97 strict / 0.90 lenient, kept precision 0.64 (NOT a measurement). Not built: per-question (Ask) eval, coverage vs chatbot, wiring results into `/status`, labeled sets for fusion/math.
2. ~~Wire front end to backend~~ done: `http.ts`, `VITE_API_URL`, UI shows "n/a" for unscored criteria and handles null evaluation/ingest times and empty links. Verified in the browser with live data (digest, ask, feedback saved to SQLite, system page).
3. **Stage 2 ranking:** Claude scores novelty/rigor/accessibility against the lens rubric (needs `ANTHROPIC_API_KEY`; track token cost for the status page).
4. **bioRxiv ingest** (worm lens lists it; status shows 0 papers).
5. **Worm filter tuning:** passing mentions of "odor"/"chemotaxis" still pass as "maybe" (seizure, lifespan papers); aging penalty can sink real chemosensation papers; consider an odorant-compound list. Tune against the eval set, not by hand.
6. **Cross-lens links** (endpoint returns `[]`), feedback-driven re-ranking, scheduled nightly ingest, voice button (disabled).
7. Untested: arXiv ingest for compbio/space/aisafety lenses; full build against the backend.
8. Backend CORS allows any localhost port. Preview configs for backend and `frontend-live` are in `.claude/launch.json`.

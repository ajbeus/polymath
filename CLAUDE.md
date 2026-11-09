# CLAUDE.md

Guidance for working in this repo.

## What this is
Polymath is a multi-topic science literature assistant (course project, CSE 455). A "lens" is a topic with its own sources, keywords, and scoring rubric. The front end currently runs entirely on **fake sample data**. There is no backend, no network fetching, and no API keys.

## Rules
- **Run the evaluation harness after any ranking change.** The harness is `eval/run_eval.py` (see `eval/README.md`); run `backend/.venv/Scripts/python eval/run_eval.py worm` and report the change in metrics. This applies to anything touching scoring, rubric weights, lens keywords, filters, or prompts. Only human labels count as a measurement: Claude's `claude_guess` labels are provisional.
- Never invent citations. Placeholder papers must stay obviously fake (`SAMPLE-` ids, "Sample Paper" titles, no URLs). Every screen showing placeholder content must show the **Sample data** badge.
- The `showcase` build must contain no personal data. Full-only lens configs and fixtures live in `lenses/full/` and `frontend/src/api/fixtures/full/` so they are never bundled into showcase.
- App and assistant names come from config (`frontend/src/config/app.ts`, env `VITE_APP_NAME`, `VITE_ASSISTANT_NAME`). Do not hardcode them in components.
- The UI talks to data only through `frontend/src/api/index.ts` (`PolymathApi`). Components never import fixtures.

## Architecture
```
polymath/
  frontend/            React + TypeScript + Vite + Tailwind v4
    src/types.ts       Paper, Lens, Digest, CrossLensLink, FeedbackEvent, SystemStatus
    src/api/index.ts   PolymathApi interface (lenses, digest, ask, feedback, links, status)
    src/api/mock.ts    Mock implementation: reads JSON fixtures, adds artificial delay
    src/api/fixtures/  <tier>/<lensId>.json (digest + papers), links.json, status.json
    src/config/app.ts  build flag and display names
    src/components, src/views, src/hooks
  lenses/              Lens configs: showcase/*.json, full/*.json (shared with the future backend)
  backend/             FastAPI service implementing the same endpoints (Python, SQLite + FTS5)
    app/main.py        routes: /lenses, /lenses/{id}/digest, /ask, /feedback, /links, /status
    app/service.py     builds responses from the DB (real data only, nothing invented)
    app/models.py      pydantic models, camelCase JSON mirroring frontend/src/types.ts
    app/db.py          schema: papers, raw_records, paper_lens, feedback, ingest_runs, papers_fts
    app/sources/       arxiv.py, pubmed.py (ingest + parsing); bioRxiv not built yet
    app/filters/       lens-specific scorers (worm_voc.py, ported from abstract_parser.py)
    app/scoring.py     stage-1 scoring: assigns papers to lenses
    app/ingest.py      ingest CLI
    data/              polymath.sqlite (git-ignored)
  eval/                labeled pools (eval/<lens>/pool.csv) and the harness (run_eval.py, build_pool.py)
```
Adding a lens = add `lenses/<tier>/<id>.json` and `frontend/src/api/fixtures/<tier>/<id>.json`. No code changes. Rubric criteria and weights come from the lens config and drive the score tooltip, breakdown bars, and the "How this lens scores" panel.

Swapping in the real backend = write an `http` implementation of `PolymathApi` and change the one `export const api` line in `src/api/index.ts`. Suggested routes are in comments there.

## Commands (run from `frontend/`)
```
npm install
npm run dev              # uses VITE_BUILD from ../.env (default: showcase)
npm run dev:showcase     # worm lab, fusion, math
npm run dev:full         # all lenses
npm run build:showcase   # typecheck + production build
npm run build:full
npm run typecheck
```
Env file: copy `.env.example` to `.env` at the repo root.

## Backend commands (run from `backend/`)
```
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # once (Windows)
.venv/Scripts/python -m app.ingest --source arxiv                 # all arXiv lenses in the build
.venv/Scripts/python -m app.ingest --source arxiv --lens fusion --days 30 --max 200
.venv/Scripts/python -m app.ingest --source pubmed --lens worm
.venv/Scripts/python -m app.ingest --rescore                      # after editing lens keywords/filters
.venv/Scripts/python -m uvicorn app.main:app --port 8765          # API (port 8000 is often taken)
```
The backend reads `VITE_BUILD` from the root `.env`, so showcase/full applies to both sides. Lens configs gain backend-only fields (`arxiv`, `pubmed`, `filter`) that the API does not expose.

Stage 1 only: scoring is keyword rules and BM25, only the `relevance` rubric criterion is populated, and `evaluation`, `nextIngestAt` and cross-lens links are empty/null. The front end uses the backend when `VITE_API_URL` is set (`npm run dev:live`), and the mock otherwise. The UI must keep tolerating missing rubric criteria, null `evaluation`/ingest times, and empty links.

## Conventions
- Colours come from CSS variables in `src/index.css` (light and dark). The per-lens accent is set on `:root` as `--accent`.
- Keep components keyboard accessible: real buttons, `aria-pressed` for toggles, visible focus, tooltips reachable by focus.
- Fixtures in `frontend/src/api/fixtures/` are generated by hand or script; keep scores consistent with the lens rubric weights.

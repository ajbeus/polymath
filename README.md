# Polymath

A multi-topic science literature assistant. Polymath continuously pulls new papers from arXiv, PubMed, and bioRxiv, ranks them against a topic-specific rubric, and delivers a cited weekly digest and per-question paper recommendations.

Pick a topic (a "lens") at the top of the screen, and everything below changes to match: the digest, the recommended papers, and the cross-lens connections.

> **Status:** early development. The front end currently runs on clearly labeled sample data. The ingestion, ranking, and evaluation pipeline is being built in stages.

## Why it's more than a chatbot

- **It monitors on its own.** New papers are ingested on a schedule, so it knows what changed since your last visit instead of relying on a live search.
- **It only recommends real papers.** Every result comes from its own index with a real ID, so it can't invent a citation.
- **It learns from feedback.** Read, skip, and save signals tune the ranking over time.
- **It's measured.** Quality is tested against a hand-labeled set and benchmarked head-to-head against general-purpose chatbots on citation validity, coverage, and recency.

## Features

- Lens toggle with per-topic rubrics (worm lab, fusion, math, and more)
- Weekly digest with scored paper cards and a "why this matched" explanation
- Ask-anything mode: papers ranked for a specific question
- Cross-lens links: the same method showing up in different fields
- System page: pipeline status, evaluation metrics, and cost tracking
- Voice interface (planned)

## Architecture

```
Sources (arXiv, PubMed, bioRxiv)
        -> Ingest and dedupe (nightly)
        -> Paper store (text and embeddings)
        -> Active lens
        -> Stage 1: fast filter (keywords + embeddings)
        -> Stage 2: Claude scorer (rubric score + reason)
        -> Weekly digest / Ask anything / Cross-lens links

Alongside: feedback log and evaluation harness
```

A lens is just a config file (sources, keywords, rubric criteria and weights, accent color), so adding a new topic means adding config and fixtures, not new code.

The front end talks to everything through a typed API layer. It uses a mock backed by JSON fixtures today, and will be swapped for a real Python backend with the same endpoints.

## Repo layout

```
polymath/
  frontend/   React + TypeScript + Vite + Tailwind
  backend/    (planned) ingestion, ranking, API
  lenses/     (planned) per-topic config files
  eval/       (planned) labeled sets and benchmarks
```

## Getting started

```bash
git clone <this-repo-url>
cd polymath/frontend
npm install
cp ../.env.example .env
npm run dev
```

### Builds

Set `VITE_BUILD` in `.env`:

- `showcase`: a curated set of lenses with no personal data, for presenting
- `full`: all lenses

## Roadmap

1. Front end with sample data (in progress)
2. Ingestion pipeline and paper store
3. Two-stage ranking and the labeled evaluation set
4. Ask-anything mode and feedback logging
5. Head-to-head benchmark against general-purpose chatbots
6. Cross-lens links and demo mode; voice as a stretch

## License

TBD

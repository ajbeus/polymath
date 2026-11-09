"""API models. JSON is camelCase and mirrors frontend/src/types.ts.

Where the real backend cannot yet produce a value the mock faked, the field is Optional
(see Evaluation, SourceStatus.last_ingest_at) and the front end must handle null.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SourceId = Literal["arxiv", "pubmed", "biorxiv"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RubricCriterion(CamelModel):
    id: str
    label: str
    weight: float
    description: str


class Lens(CamelModel):
    id: str
    name: str
    short_name: str
    description: str
    sources: list[SourceId]
    keywords: list[str]
    ask_examples: list[str] = []
    rubric: list[RubricCriterion]
    accent: str
    builds: list[str]
    order: int


class LensConfig(Lens):
    """A lens as stored on disk: the public fields plus backend-only ingest settings."""

    arxiv: Optional[dict] = None    # {"categories": [...], "useKeywords": bool}
    pubmed: Optional[dict] = None   # {"query": "..."}
    filter: Optional[str] = None    # name of a lens-specific scorer in app/filters


class Paper(CamelModel):
    id: str
    lens_id: str
    title: str
    authors: list[str]
    source: SourceId
    date: str
    score: float
    summary: str
    why_matched: str
    # Only criteria that have actually been scored appear here. Stage 1 scores relevance only.
    rubric: dict[str, float]
    url: Optional[str] = None
    is_sample: bool = False


class SinceLastVisit(CamelModel):
    text: str
    new_papers: int
    reranked: int


class Digest(CamelModel):
    lens_id: str
    week_of: str
    generated_at: str
    summary: str
    since_last_visit: SinceLastVisit
    recommended: list[Paper]
    others: list[Paper]
    is_sample: bool = False


class AskRequest(CamelModel):
    question: str
    lens_id: Optional[str] = None


class AskResult(CamelModel):
    question: str
    lens_id: Optional[str]
    results: list[Paper]
    took_ms: int
    note: str
    is_sample: bool = False


class LinkPaper(CamelModel):
    id: str
    lens_id: str
    title: str
    source: SourceId
    date: str
    is_sample: bool = False


class CrossLensLink(CamelModel):
    id: str
    method: str
    explanation: str
    lens_ids: list[str]
    papers: list[LinkPaper]
    strength: float
    is_sample: bool = False


class FeedbackEvent(CamelModel):
    paper_id: str
    lens_id: str
    action: Literal["read", "skip", "save"]
    active: bool
    at: str


class SourceStatus(CamelModel):
    source: SourceId
    indexed: int
    added_last24h: int = Field(alias="addedLast24h")
    last_ingest_at: Optional[str]
    state: Literal["ok", "delayed", "error"]


class PerLens(CamelModel):
    lens_id: str
    indexed: int


class Evaluation(CamelModel):
    k: int
    precision_at_k: float
    ndcg: float
    citation_validity: float
    coverage: dict[str, float]
    labeled_queries: int
    last_run_at: str


class CostDay(CamelModel):
    date: str
    usd: float
    tokens_in: int
    tokens_out: int


class Cost(CamelModel):
    budget_usd_per_day: float
    days: list[CostDay]


class SystemStatus(CamelModel):
    is_sample: bool = False
    last_ingest_at: Optional[str]
    next_ingest_at: Optional[str]
    sources: list[SourceStatus]
    per_lens: list[PerLens]
    evaluation: Optional[Evaluation]  # null until the eval harness exists
    cost: Cost

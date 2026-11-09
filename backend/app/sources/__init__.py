from dataclasses import dataclass, field


@dataclass
class PaperRecord:
    """A paper as parsed from a source, before it is scored against any lens."""

    id: str                 # '<source>:<external_id>'
    source: str             # arxiv | pubmed | biorxiv
    external_id: str
    title: str
    abstract: str
    published: str          # YYYY-MM-DD
    authors: list[str] = field(default_factory=list)
    url: str | None = None
    doi: str | None = None
    categories: list[str] = field(default_factory=list)  # arXiv categories or MeSH headings
    extras: dict = field(default_factory=dict)            # source-specific, used by lens filters
    raw_format: str = "xml"
    raw_body: str = ""      # the untouched source record, kept so parsing can be re-run offline

from dataclasses import dataclass

@dataclass(frozen=True)
class Document:
    text: str
    source: str
    page: int | None = None

@dataclass(frozen=True)
class Chunk:
    text: str
    source: str
    chunk_id: str
    chunk_index: int
    page: int | None = None

@dataclass(frozen=True)
class SearchResult:
    text: str
    source: str
    chunk_id: str
    score: float
    page: int | None = None

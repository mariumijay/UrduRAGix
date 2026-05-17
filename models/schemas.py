"""
Pydantic v2 request/response schemas for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional

SUPPORTED_DATASETS: frozenset[str] = frozenset({"urdu_A", "urdu_B"})


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    book_title:  str = Field(default="", description="Title of the Urdu book")
    author:      str = Field(default="", description="Author name")
    chapter:     str = Field(default="", description="Chapter name or number")
    page_start:  int = Field(default=1,  description="Starting page number")
    chunk_size:  int = Field(default=400, ge=100, le=1000)
    overlap:     int = Field(default=50,  ge=0,   le=200)
    dataset:     str = Field(
        default="urdu_A",
        description="Target dataset for ingestion. Must be one of: urdu_A, urdu_B",
    )

    @field_validator("dataset")
    @classmethod
    def validate_dataset(cls, v: str) -> str:
        if v not in SUPPORTED_DATASETS:
            raise ValueError(
                f"Invalid dataset '{v}'. "
                f"Supported datasets are: {sorted(SUPPORTED_DATASETS)}"
            )
        return v


class IngestResponse(BaseModel):
    status:          str
    chunks_indexed:  int
    embedding_dim:   int
    faiss_total:     int
    message:         str


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query:   str  = Field(..., min_length=2, description="Urdu question")
    top_k:   int  = Field(default=5, ge=1, le=20)
    stream:  bool = Field(default=False)
    genre:   Optional[str] = Field(default=None)


class CitationSchema(BaseModel):
    chunk_id:     str
    page_start:   int
    book_title:   str
    chapter:      str
    text_preview: str


class QueryResponse(BaseModel):
    answer:    str
    citations: list[CitationSchema]
    model:     str
    usage:     dict


# ---------------------------------------------------------------------------
# Chunks
# ---------------------------------------------------------------------------

class ChunkSchema(BaseModel):
    chunk_id:    str
    text:        str
    token_count: int
    book_title:  str
    author:      str
    page_start:  int
    page_end:    int
    chapter:     str
    position:    int


class ChunksResponse(BaseModel):
    total:  int
    chunks: list[ChunkSchema]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status:         str
    faiss_vectors:  Optional[int]
    chunks_count:   Optional[int]
    bm25_ready:     bool
    embedding_model: str
    llm_model:      str
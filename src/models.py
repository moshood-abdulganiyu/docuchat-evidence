from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class QueryRequest(BaseModel):
    question: Question
    k: int = Field(default=5, ge=1, le=10)


class Citation(BaseModel):
    n: int
    file: str
    page: int


class RetrievedChunk(BaseModel):
    id: str
    score: float
    file: str
    page: int


class QueryResponse(BaseModel):
    answer: str
    found: bool
    reason: Literal["gate", "model", "empty"] | None = None
    citations: list[Citation]
    uncited: bool = False
    retrieved: list[RetrievedChunk]


class HealthResponse(BaseModel):
    status: str

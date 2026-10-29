from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from src.sessions import is_valid_session_id

Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class QueryRequest(BaseModel):
    question: Question
    k: int = Field(default=5, ge=1, le=10)
    session_id: str | None = None
    history: list[Turn] = Field(default_factory=list, max_length=20)

    @field_validator("session_id")
    @classmethod
    def _check_session_id(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_session_id(v):
            raise ValueError("invalid session id")
        return v


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


class UploadResponse(BaseModel):
    session_id: str
    file: str
    pages: int
    chunks: int
    files_in_session: int

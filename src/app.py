import logging

from fastapi import FastAPI, HTTPException

from src.models import HealthResponse, QueryRequest, QueryResponse
from src.rag import rag_answer

log = logging.getLogger("docuchat")

DEMO_NAMESPACE = "demo"

app = FastAPI(title="DocuChat Evidence", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


# Plain "def" on purpose: rag_answer blocks (Pinecone, Gemini, retry sleeps),
# so FastAPI runs it in a worker thread instead of freezing the event loop.
@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    try:
        result = rag_answer(req.question, namespace=DEMO_NAMESPACE, k=req.k)
    except Exception as exc:
        log.exception("query failed")
        if getattr(exc, "code", None) == 429:
            raise HTTPException(
                status_code=503,
                detail="The language model is rate limited. Try again in a minute.",
            )
        raise HTTPException(
            status_code=502, detail="The answer service failed. Try again."
        )
    return QueryResponse(
        answer=result["answer"],
        found=result["found"],
        reason=result["reason"],
        citations=result["citations"],
        uncited=result["uncited"],
        retrieved=result["retrieved"],
    )

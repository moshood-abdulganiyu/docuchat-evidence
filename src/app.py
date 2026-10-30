import hmac
import logging
import os
import time
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src.cleanup import delete_expired
from src.indexing import ChunkLimitError, index_pages, list_session_files
from src.logs import event
from src.models import HealthResponse, QueryRequest, QueryResponse, UploadResponse
from src.pdf_pages import extract_pages, safe_filename
from src.rag import rag_answer
from src.rewrite import MAX_HISTORY, rewrite_question
from src.sessions import (
    MAX_BYTES,
    MAX_CHUNKS_PER_FILE,
    MAX_FILES,
    is_valid_session_id,
    new_session_id,
)

log = logging.getLogger("docuchat")

DEMO_NAMESPACE = "demo"

app = FastAPI(title="DocuChat Evidence", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    # session_id was validated by QueryRequest, so it can never be "demo".
    namespace = req.session_id if req.session_id else DEMO_NAMESPACE
    # The session id is the only access control, so it is never logged.
    mode = "demo" if namespace == DEMO_NAMESPACE else "session"
    history = req.history[-MAX_HISTORY:]
    t0 = time.perf_counter()
    try:
        standalone = (
            rewrite_question(req.question, history) if history else req.question
        )
        t1 = time.perf_counter()
        result = rag_answer(standalone, namespace=namespace, k=req.k)
        t2 = time.perf_counter()
    except Exception as exc:
        code = getattr(exc, "code", None)
        log.exception("query failed")
        event(
            "query_error",
            mode=mode,
            error_type=type(exc).__name__,
            error_code=code if isinstance(code, int) else None,
        )
        if code == 429:
            raise HTTPException(
                status_code=503,
                detail="The language model is rate limited. Try again in a minute.",
            )
        raise HTTPException(
            status_code=502, detail="The answer service failed. Try again."
        )

    # Counts, scores and timings only. No question, answer or document text.
    scores = [r["score"] for r in result["retrieved"]]
    event(
        "query",
        mode=mode,
        found=result["found"],
        reason=result["reason"],
        k=req.k,
        retrieved=len(scores),
        top_score=round(max(scores), 3) if scores else None,
        cited=len(result["citations"]),
        uncited=result["uncited"],
        rewritten=bool(history),
        rewrite_ms=round((t1 - t0) * 1000),
        rag_ms=round((t2 - t1) * 1000),
    )
    return QueryResponse(
        answer=result["answer"],
        found=result["found"],
        reason=result["reason"],
        citations=result["citations"],
        uncited=result["uncited"],
        retrieved=result["retrieved"],
        rewritten_question=standalone if history else None,
    )


@app.post("/upload", response_model=UploadResponse)
def upload(
    file: Annotated[UploadFile, File()],
    session_id: Annotated[str | None, Form()] = None,
) -> UploadResponse:
    name = safe_filename(file.filename or "")
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only .pdf files are accepted.")

    data = file.file.read(MAX_BYTES + 1)  # bounded read
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 4 MB.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File is not a PDF.")

    session_id = (session_id or "").strip() or None
    if session_id is None:
        session_id, existing = new_session_id(), set()
    elif not is_valid_session_id(session_id):
        raise HTTPException(status_code=422, detail="Invalid session id.")
    else:
        try:
            existing = list_session_files(session_id)
        except Exception:
            log.exception("list_session_files failed")
            raise HTTPException(status_code=502, detail="Upload failed.")

    if name in existing:
        raise HTTPException(
            status_code=409, detail="A file with this name is already in the session."
        )
    if len(existing) >= MAX_FILES:
        raise HTTPException(status_code=409, detail="A session holds at most 5 files.")

    try:
        pages = extract_pages(data, name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Could not read the PDF: {exc}.")
    if not pages:
        raise HTTPException(
            status_code=422,
            detail="No text found. Scanned PDFs without a text layer are not supported.",
        )

    try:
        n_chunks = index_pages(pages, session_id, max_chunks=MAX_CHUNKS_PER_FILE)
    except ChunkLimitError as exc:
        raise HTTPException(
            status_code=422, detail=f"PDF is too long to index ({exc})."
        )
    except Exception:
        log.exception("indexing failed")
        raise HTTPException(status_code=502, detail="Upload failed.")

    return UploadResponse(
        session_id=session_id,
        file=name,
        pages=len(pages),
        chunks=n_chunks,
        files_in_session=len(existing) + 1,
    )


@app.get("/api/cron/cleanup", include_in_schema=False)
def cron_cleanup(authorization: str | None = Header(default=None)):
    secret = os.environ.get("CRON_SECRET")
    expected = f"Bearer {secret}" if secret else None
    if (
        not expected
        or not authorization
        or not hmac.compare_digest(authorization, expected)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return delete_expired()


logging.basicConfig(level=logging.INFO)


@app.middleware("http")
async def access_log(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if request.url.path in ("/query", "/upload"):
        ms = round((time.perf_counter() - start) * 1000)
        event("request", path=request.url.path, status=response.status_code, ms=ms)
    return response


if not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory="public", html=True), name="public")

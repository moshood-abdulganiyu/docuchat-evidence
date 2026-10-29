import logging
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from src.indexing import ChunkLimitError, index_pages, list_session_files
from src.models import HealthResponse, QueryRequest, QueryResponse, UploadResponse
from src.pdf_pages import extract_pages, safe_filename
from src.rag import rag_answer
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


# Plain "def" on purpose: rag_answer blocks (Pinecone, Gemini, retry sleeps),
# so FastAPI runs it in a worker thread instead of freezing the event loop.
@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    # session_id was validated by QueryRequest, so it can never be "demo".
    namespace = req.session_id if req.session_id else DEMO_NAMESPACE
    try:
        result = rag_answer(req.question, namespace=namespace, k=req.k)
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

from src.chunking import chunk_page
from src.embeddings import embed
from src.store import get_index

# PLACEHOLDERS: use the same values index_corpus.py passes to chunk_page.
# README says 500 chars, 20% overlap. Check whether overlap_pct expects 20 or 0.2.
CHUNK_SIZE = 500
OVERLAP_PCT = 0.20
BATCH = 64


class ChunkLimitError(Exception):
    pass


def build_chunks(pages: list[dict]) -> list[dict]:
    out = []
    for p in pages:
        # assumes chunk_page returns list[str]
        for idx, text in enumerate(chunk_page(p["text"], CHUNK_SIZE, OVERLAP_PCT)):
            out.append(
                {
                    "id": f"{p['file']}:p{p['page']}:c{idx}",
                    "file": p["file"],
                    "page": p["page"],
                    "chunk": idx,
                    "text": text,
                }
            )
    return out


def index_pages(
    pages: list[dict], namespace: str, max_chunks: int | None = None
) -> int:
    chunks = build_chunks(pages)
    if max_chunks is not None and len(chunks) > max_chunks:
        raise ChunkLimitError(f"{len(chunks)} chunks, limit {max_chunks}")
    index = get_index()
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        vectors = embed([c["text"] for c in batch], kind="document")
        index.upsert(
            vectors=[
                {
                    "id": c["id"],
                    "values": [float(x) for x in v],
                    "metadata": {
                        "file": c["file"],
                        "page": c["page"],
                        "chunk": c["chunk"],
                        "text": c["text"],
                    },
                }
                for c, v in zip(batch, vectors)
            ],
            namespace=namespace,
        )
    return len(chunks)


def list_session_files(namespace: str) -> set[str]:
    """Distinct file names in a namespace, parsed from ids 'file:pPAGE:cIDX'."""
    files = set()
    for ids in get_index().list(namespace=namespace):
        for vid in ids:
            files.add(vid.rsplit(":p", 1)[0])
    return files

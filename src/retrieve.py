"""Top-k retrieval from a Pinecone namespace."""

import argparse

from src.embeddings import embed
from src.store import get_index


def retrieve(question: str, namespace: str = "demo", k: int = 5) -> list[dict]:
    """Return the top-k chunks for a question as dicts:
    score, file, page, chunk, text, id. Sorted by score, highest first."""
    vector = [float(x) for x in embed([question], kind="query")[0]]
    result = get_index().query(
        vector=vector,
        top_k=k,
        namespace=namespace,
        include_metadata=True,
    )
    hits = []
    for m in result.matches:
        md = m.metadata or {}
        hits.append(
            {
                "id": m.id,
                "score": float(m.score),
                "file": md.get("file"),
                "page": int(md["page"]) if md.get("page") is not None else None,
                "chunk": int(md["chunk"]) if md.get("chunk") is not None else None,
                "text": md.get("text", ""),
            }
        )
    return hits


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--namespace", default="demo")
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()
    for h in retrieve(args.question, args.namespace, args.k):
        print(f"{h['score']:.3f}  {h['file']}  p{h['page']}  {h['text'][:90]!r}")

"""Chunk the demo corpus, embed it, and upsert into the Pinecone 'demo' namespace."""

import argparse
import json

from src.chunking import chunk_page
from src.embeddings import embed
from src.store import get_index

SIZE, OVERLAP, NAMESPACE = 500, 0.20, "demo"


def build_chunks() -> list[dict]:
    rows = []
    with open("data/pages.jsonl", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            for i, text in enumerate(chunk_page(p["text"], SIZE, OVERLAP)):
                rows.append(
                    {
                        "id": f"{p['file']}:p{p['page']}:c{i}",
                        "file": p["file"],
                        "page": p["page"],
                        "chunk_index": i,
                        "text": text,
                    }
                )
    return rows


def index_all(limit: int | None = None) -> None:
    rows = build_chunks()[:limit]
    index = get_index()
    for i in range(0, len(rows), 64):
        batch = rows[i : i + 64]
        vectors = embed([r["text"] for r in batch])
        index.upsert(
            vectors=[
                {
                    "id": r["id"],
                    "values": v,
                    "metadata": {
                        k: r[k] for k in ("file", "page", "chunk_index", "text")
                    },
                }
                for r, v in zip(batch, vectors)
            ],
            namespace=NAMESPACE,
        )
        print(f"{min(i + 64, len(rows))}/{len(rows)}")
    print(index.describe_index_stats())


def check(question: str) -> None:
    res = get_index().query(
        vector=embed([question], kind="query")[0],
        top_k=3,
        namespace=NAMESPACE,
        include_metadata=True,
    )
    for m in res.matches:
        md = m.metadata
        print(f"{m.score:.3f} {md['file']} p.{int(md['page'])}: {md['text'][:150]}...")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--check", type=str)
    a = ap.parse_args()
    check(a.check) if a.check else index_all(a.limit)

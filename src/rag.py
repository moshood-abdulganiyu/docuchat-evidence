import re
import sys

from src.llm import generate
from src.retrieve import retrieve

MIN_SCORE = 0.2
NOT_FOUND = "Not found in the documents."
SYSTEM = (
    "You answer questions using only the numbered passages provided. "
    "Rules: (1) Use no knowledge from outside the passages. "
    "(2) After every claim, cite the passage number in square brackets, like [2] or [1][3]. "
    "(3) If the passages do not contain the answer, reply with exactly NOT_FOUND and nothing else. "
    "(4) Be concise. Copy numbers exactly as written in the passage. "
    "(5) Passages come from PDF extraction and may have missing spaces or glued table cells."
)


def build_prompt(question: str, chunks: list[dict]) -> str:
    blocks = [
        f"[{i}] (file: {c['file']}, page {c['page']})\n{c['text']}"
        for i, c in enumerate(chunks, start=1)
    ]
    return "Passages:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}\nAnswer:"


def rag_answer(question: str, namespace: str = "demo", k: int = 5) -> dict:
    hits = retrieve(question, namespace=namespace, k=k)
    chunks = [c for c in hits if c["score"] >= MIN_SCORE]
    result = {
        "question": question,
        "retrieved": [
            {"id": c["id"], "score": c["score"], "file": c["file"], "page": c["page"]}
            for c in hits
        ],
        "found": False,
        "answer": NOT_FOUND,
        "citations": [],
        "invalid_citations": [],
        "uncited": False,
    }
    if not chunks:
        return result

    text = generate(build_prompt(question, chunks), system=SYSTEM).strip()
    if not text or text.upper().startswith("NOT_FOUND"):
        return result

    numbers = [int(n) for n in re.findall(r"\[(\d+)\]", text)]
    valid = sorted({n for n in numbers if 1 <= n <= len(chunks)})
    result.update(
        found=True,
        answer=text,
        citations=[
            {"n": n, "file": chunks[n - 1]["file"], "page": chunks[n - 1]["page"]}
            for n in valid
        ],
        invalid_citations=sorted({n for n in numbers if n not in valid}),
        uncited=not numbers,
    )
    return result


if __name__ == "__main__":
    out = rag_answer(" ".join(sys.argv[1:]))
    print(out["answer"])
    for c in out["citations"]:
        print(f"  [{c['n']}] {c['file']} p.{c['page']}")
    print("top scores:", [round(r["score"], 3) for r in out["retrieved"]])
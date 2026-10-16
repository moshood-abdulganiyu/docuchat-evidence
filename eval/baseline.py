import json
import time
from datetime import UTC, datetime
from pathlib import Path

from src.llm import MODEL, generate

QUESTIONS = Path("eval/questions.jsonl")
OUT = Path("eval/baseline_answers.jsonl")
PAUSE_SECONDS = 7
SYSTEM = (
    "Answer the question directly and concisely from your own knowledge. "
    "If you do not know, say you do not know. Do not ask for a document."
)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def main() -> None:
    done = {row["id"] for row in read_jsonl(OUT)}
    for q in read_jsonl(QUESTIONS):
        if q["id"] in done:
            continue
        answer = generate(q["question"], system=SYSTEM)
        row = {
            "id": q["id"],
            "question": q["question"],
            "answer": answer,
            "model": MODEL,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(q["id"], "empty answer" if not answer else f"{len(answer)} chars")
        time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()

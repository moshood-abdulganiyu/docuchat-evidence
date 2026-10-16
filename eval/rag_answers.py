import json
import time
from datetime import UTC, datetime
from pathlib import Path

from src.llm import MODEL
from src.rag import rag_answer

QUESTIONS = Path("eval/questions.jsonl")
OUT = Path("eval/rag_answers.jsonl")
PAUSE_SECONDS = 7


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
        res = rag_answer(q["question"])
        res.update(id=q["id"], model=MODEL, timestamp=datetime.now(UTC).isoformat())
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
        flags = []
        if not res["found"]:
            flags.append("NOT FOUND")
        if res["invalid_citations"]:
            flags.append("bad citation")
        if res["uncited"]:
            flags.append("uncited")
        print(q["id"], len(res["answer"]), "chars", " ".join(flags))
        time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()

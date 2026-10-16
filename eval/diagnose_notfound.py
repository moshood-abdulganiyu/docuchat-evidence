import json
import time
from pathlib import Path

from src.rag import rag_answer

ROWS = Path("eval/rag_answers.jsonl")
OUT = Path("eval/notfound_diagnosis.jsonl")
PAUSE_SECONDS = 7


def main() -> None:
    lines = ROWS.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    targets = [r for r in rows if not r["found"]]
    with OUT.open("w", encoding="utf-8") as f:
        for r in targets:
            res = rag_answer(r["question"])
            res["id"] = r["id"]
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            scores = [round(h["score"], 3) for h in res["retrieved"]]
            print(
                r["id"],
                "reason:", res["reason"],
                "| chunks_used:", res["chunks_used"],
                "| found on rerun:", res["found"],
                "| scores:", scores,
            )
            if res["reason"] != "gate":
                time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
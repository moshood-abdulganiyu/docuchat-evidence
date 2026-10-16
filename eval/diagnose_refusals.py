import json
import re
from pathlib import Path

from src.retrieve import retrieve

IDS = ["q01", "q03", "q06", "q07", "q13", "q16"]


def main() -> None:
    lines = Path("eval/questions.jsonl").read_text(encoding="utf-8").splitlines()
    questions = {q["id"]: q for q in (json.loads(x) for x in lines if x.strip())}
    for qid in IDS:
        q = questions[qid]
        patterns = q.get("answer_patterns", [])
        hits = retrieve(q["question"], k=5)
        print(f"\n{qid}: {q['question']}")
        print(f"  gold file: {q.get('gold_file')}  patterns: {patterns}")
        joined = " ".join(h["text"] for h in hits)
        for rank, h in enumerate(hits, start=1):
            matched = sum(
                bool(re.search(p, h["text"], re.IGNORECASE)) for p in patterns
            )
            same_file = h["file"] == q.get("gold_file")
            print(
                f"  rank {rank}: gold file={same_file} page={h['page']} "
                f"patterns in chunk={matched}/{len(patterns)}"
            )
        all_in_one = any(
            patterns and all(re.search(p, h["text"], re.IGNORECASE) for p in patterns)
            for h in hits
        )
        across = patterns and all(re.search(p, joined, re.IGNORECASE) for p in patterns)
        print(
            f"  all patterns in one chunk: {all_in_one} | across the 5 chunks: {bool(across)}"
        )
        gold_chunks = [h for h in hits if h["file"] == q.get("gold_file")]
        if gold_chunks:
            print(
                "  top gold-file chunk:",
                gold_chunks[0]["text"][:300].replace("\n", " "),
            )


if __name__ == "__main__":
    main()

import csv
import json
import re
from pathlib import Path


def read_jsonl(path: str) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines if x.strip()]


def baseline_abstained(answer: str) -> bool:
    return (
        bool(re.search(r"\bi (do not|don't) know\b", answer, re.IGNORECASE))
        and len(answer) < 200
    )


def main() -> None:
    questions = read_jsonl("eval/questions.jsonl")
    base = {r["id"]: r for r in read_jsonl("eval/baseline_answers.jsonl")}
    rag = {r["id"]: r for r in read_jsonl("eval/rag_answers.jsonl")}
    with open("eval/scoring_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "question",
                "gold_file",
                "gold_page",
                "baseline_answer",
                "baseline_score",
                "rag_answer",
                "rag_cited",
                "rag_score",
                "citation_ok",
            ]
        )
        for q in questions:
            if q["id"] == "q05":
                continue
            b, r = base[q["id"]], rag[q["id"]]
            cited = "; ".join(f"{c['file']} p.{c['page']}" for c in r["citations"])
            w.writerow(
                [
                    q["id"],
                    q["question"],
                    q.get("gold_file"),
                    q.get("gold_page"),
                    b["answer"],
                    "abstained" if baseline_abstained(b["answer"]) else "",
                    r["answer"],
                    cited,
                    "" if r["found"] else "abstained",
                    "",
                ]
            )
    print("wrote eval/scoring_sheet.csv")


if __name__ == "__main__":
    main()

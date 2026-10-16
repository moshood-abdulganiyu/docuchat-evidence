import csv
import json
import re
import sys
from pathlib import Path

SHEET = Path("eval/scoring_sheet.csv")
OK = {"correct", "wrong"}


def main() -> None:
    judgments = dict(a.split("=") for a in sys.argv[1:])
    bad = {k: v for k, v in judgments.items() if v not in OK}
    if bad:
        sys.exit(f"values must be correct or wrong: {bad}")
    lines = Path("eval/questions.jsonl").read_text(encoding="utf-8").splitlines()
    qs = {q["id"]: q for q in (json.loads(x) for x in lines if x.strip())}
    with SHEET.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    for r in rows:
        qid = r["id"]
        if f"baseline_{qid}" in judgments:
            r["baseline_score"] = judgments[f"baseline_{qid}"]
        if qid in judgments and r["rag_score"] != "abstained":
            r["rag_score"] = judgments[qid]
        if r["rag_score"] != "abstained" and not r["citation_ok"]:
            cited = re.findall(r"(\S+\.pdf) p\.(\d+)", r["rag_cited"])
            gold = (qs[qid]["gold_file"], int(qs[qid]["gold_page"]))
            r["citation_ok"] = (
                "y" if any((fn, int(pg)) == gold for fn, pg in cited) else "n"
            )

    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    missing = [r["id"] for r in rows if not r["baseline_score"] or not r["rag_score"]]
    if missing:
        print("still unscored:", missing)
    n = len(rows)
    for name, col in (("No retrieval", "baseline_score"), ("RAG", "rag_score")):
        c = {
            v: sum(r[col] == v for r in rows) for v in ("correct", "abstained", "wrong")
        }
        print(
            f"{name:13} correct {c['correct']}/{n}  abstained {c['abstained']}/{n}  wrong {c['wrong']}/{n}"
        )
    answered = [r for r in rows if r["rag_score"] in OK]
    ok = sum(r["citation_ok"] == "y" for r in answered)
    print(f"Citation on gold page: {ok}/{len(answered)} answered RAG rows")


if __name__ == "__main__":
    main()

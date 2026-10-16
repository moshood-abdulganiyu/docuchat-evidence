import csv
import json
import re
from pathlib import Path

SHEET = Path("eval/scoring_sheet.csv")


def read_jsonl(path: str) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines if x.strip()]


def main() -> None:
    qs = {q["id"]: q for q in read_jsonl("eval/questions.jsonl")}
    pages = {
        (p["file"], int(p["page"])): p["text"] for p in read_jsonl("data/pages.jsonl")
    }
    with SHEET.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    for r in rows:
        pats = qs[r["id"]].get("answer_patterns", [])

        def hit(text: str, pats: list[str] = pats) -> bool:
            return bool(pats) and all(re.search(p, text, re.IGNORECASE) for p in pats)

        if not r["baseline_score"] and hit(r["baseline_answer"]):
            r["baseline_score"] = "correct"
        if r["rag_score"] != "abstained":
            if not r["rag_score"] and hit(r["rag_answer"]):
                r["rag_score"] = "correct"
            cited = re.findall(r"(\S+\.pdf) p\.(\d+)", r["rag_cited"])
            if not r["citation_ok"] and any(
                hit(pages.get((fn, int(pg)), "")) for fn, pg in cited
            ):
                r["citation_ok"] = "y"

    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    todo = [
        r
        for r in rows
        if not r["baseline_score"]
        or (
            r["rag_score"] != "abstained"
            and (not r["rag_score"] or not r["citation_ok"])
        )
    ]
    print(f"auto-scored; {len(todo)} rows still need you:\n")
    for r in todo:
        q = qs[r["id"]]
        print(
            f"{r['id']} | baseline_score={r['baseline_score'] or '?'} "
            f"rag_score={r['rag_score'] or '?'} citation_ok={r['citation_ok'] or '?'}"
        )
        print(f"   Q: {q['question']}")
        print(f"   RAG: {r['rag_answer'][:220]}")
        print(
            f"   cited: {r['rag_cited']} | gold: {q['gold_file']} p.{q['gold_page']} "
            f"| patterns: {q.get('answer_patterns', [])}\n"
        )


if __name__ == "__main__":
    main()

"""Show what retrieval returned for every question that missed the gold page at k=5."""
import json
import sys

from src.retrieve import retrieve

sys.stdout.reconfigure(encoding="utf-8")

pages = {}
for line in open("data/pages.jsonl", encoding="utf-8"):
    p = json.loads(line)
    pages[(p["file"], p["page"])] = p["text"]

for line in open("eval/questions.jsonl", encoding="utf-8"):
    q = json.loads(line)
    hits = retrieve(q["question"], "demo", k=5)
    if any(h["file"] == q["gold_file"] and h["page"] == q["gold_page"] for h in hits):
        continue
    print(f"=== {q['id']}: {q['question']}")
    print(f"gold: {q['gold_file']} p{q['gold_page']}")
    print("gold page starts:", pages.get((q["gold_file"], q["gold_page"]), "NOT IN pages.jsonl")[:300])
    for h in hits:
        same = "same file" if h["file"] == q["gold_file"] else "other file"
        print(f"  {h['score']:.3f}  {h['file']} p{h['page']} ({same})  {h['text'][:120]!r}")
    print()
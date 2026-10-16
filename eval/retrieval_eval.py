"""Hit rate at k. Gold pages: answer_patterns (pages matching all regexes, minus
exclude_pages), else gold_pages (list), else gold_page (int)."""

import argparse
import json
import re
import sys

from src.retrieve import retrieve

sys.stdout.reconfigure(encoding="utf-8")

PAGES: dict[str, dict[int, str]] = {}
for line in open("data/pages.jsonl", encoding="utf-8"):
    p = json.loads(line)
    PAGES.setdefault(p["file"], {})[p["page"]] = p["text"]


def gold_pages(q: dict) -> set[int]:
    if "answer_patterns" in q:
        found = {
            page
            for page, text in PAGES.get(q["gold_file"], {}).items()
            if all(re.search(pat, text) for pat in q["answer_patterns"])
        }
        return found - set(q.get("exclude_pages", []))
    if "gold_pages" in q:
        return set(q["gold_pages"])
    return {q["gold_page"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespace", default="demo")
    ap.add_argument("--questions", default="eval/questions.jsonl")
    args = ap.parse_args()

    qs = [json.loads(line) for line in open(args.questions, encoding="utf-8")]
    ks = (3, 5)
    page_hits = {k: 0 for k in ks}
    file_hits = {k: 0 for k in ks}

    for q in qs:
        gp = gold_pages(q)
        hits = retrieve(q["question"], args.namespace, k=max(ks))
        rank = next(
            (
                i + 1
                for i, h in enumerate(hits)
                if h["file"] == q["gold_file"] and h["page"] in gp
            ),
            None,
        )
        frank = next(
            (i + 1 for i, h in enumerate(hits) if h["file"] == q["gold_file"]), None
        )
        for k in ks:
            page_hits[k] += rank is not None and rank <= k
            file_hits[k] += frank is not None and frank <= k
        print(
            f"{q['id']}  page rank: {rank or '-'}  file rank: {frank or '-'}"
            f"  gold pages: {sorted(gp)}"
        )

    n = len(qs)
    print(f"\nnamespace={args.namespace}  questions={n}")
    for k in ks:
        print(
            f"k={k}  file+page: {page_hits[k]}/{n} = {page_hits[k] / n:.2f}"
            f"   file only: {file_hits[k]}/{n} = {file_hits[k] / n:.2f}"
        )


if __name__ == "__main__":
    main()

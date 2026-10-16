"""Print random corpus pages so eval questions can be written from real passages."""

import argparse
import json
import random
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")


def looks_like_references(text: str) -> bool:
    cites = len(re.findall(r"\[\d+\]", text))
    return cites > 8 or text.count("et al") + text.count("arXiv") > 5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=25)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--chars", type=int, default=700)
    args = ap.parse_args()

    pages = [json.loads(line) for line in open("data/pages.jsonl", encoding="utf-8")]
    pages = [p for p in pages if not looks_like_references(p["text"])]

    by_file: dict[str, list[dict]] = {}
    for p in pages:
        by_file.setdefault(p["file"], []).append(p)

    rng = random.Random(args.seed)
    files = list(by_file)
    rng.shuffle(files)
    for f in files[: args.n]:
        p = rng.choice(by_file[f])
        print(f"=== {p['file']}  page {p['page']}")
        print(p["text"][: args.chars])
        print()


if __name__ == "__main__":
    main()

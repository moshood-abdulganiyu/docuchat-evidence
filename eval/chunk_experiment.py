import json
from statistics import mean

from src.chunking import chunk_page

CONFIGS = [(500, 0.10), (500, 0.20), (800, 0.10), (800, 0.20)]
pages = [json.loads(line) for line in open("data/pages.jsonl", encoding="utf-8")]

print("size overlap chunks mean_len pct_short pct_midsentence")
for size, ov in CONFIGS:
    chunks = [c for p in pages for c in chunk_page(p["text"], size, ov)]
    lens = [len(c) for c in chunks]
    short = sum(n < 200 for n in lens) / len(lens)
    mid = sum(c[-1] not in ".?!" for c in chunks) / len(chunks)
    print(
        f"{size:>4} {ov:>6.0%} {len(chunks):>6} {mean(lens):>8.0f} {short:>9.1%} {mid:>15.1%}"
    )

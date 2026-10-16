import json
import sys
from pathlib import Path

from tokenizers import Tokenizer

from src.chunking import chunk_page

LIMIT = 256
OVERLAP = 0.20
tok = Tokenizer.from_file(sys.argv[1])
tok.no_truncation()

pages = [
    json.loads(l)["text"]
    for l in Path("data/pages.jsonl").read_text(encoding="utf-8").splitlines()
]

print("size  chunks  mean  p95  max  over256")
for size in (500, 600, 700, 800):
    sizes = sorted(
        len(tok.encode(c).ids) for t in pages for c in chunk_page(t, size, OVERLAP)
    )
    n = len(sizes)
    over = sum(s > LIMIT for s in sizes)
    print(
        f"{size}   {n}   {sum(sizes) / n:.0f}   {sizes[int(n * 0.95)]}   {sizes[-1]}   {over} ({100 * over / n:.1f}%)"
    )

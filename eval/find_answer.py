"""List pages of one PDF whose text contains a regex."""

import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
file, pattern = sys.argv[1], sys.argv[2]
for line in open("data/pages.jsonl", encoding="utf-8"):
    p = json.loads(line)
    if p["file"] == file and re.search(pattern, p["text"]):
        i = re.search(pattern, p["text"]).start()
        print(f"p{p['page']}: ...{p['text'][max(0, i - 60) : i + 100]}...")

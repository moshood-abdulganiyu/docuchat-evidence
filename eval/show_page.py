"""Print one page of one PDF from pages.jsonl."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
file, page = sys.argv[1], int(sys.argv[2])
for line in open("data/pages.jsonl", encoding="utf-8"):
    p = json.loads(line)
    if p["file"] == file and p["page"] == page:
        print(p["text"])
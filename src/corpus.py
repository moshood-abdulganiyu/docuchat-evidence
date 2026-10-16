"""Download arXiv PDFs and extract text per page."""

import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from pypdf import PdfReader

PDF_DIR = Path("data/pdfs")
MANIFEST = Path("data/manifest.json")
PAGES = Path("data/pages.jsonl")
QUERY = 'all:"retrieval augmented generation" AND all:evaluation'
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def download(n: int = 30) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    r = httpx.get(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": QUERY,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": n,
        },
        timeout=30,
        follow_redirects=True,
    )
    r.raise_for_status()
    manifest = []
    for e in ET.fromstring(r.text).findall("a:entry", ATOM):
        arxiv_id = e.findtext("a:id", namespaces=ATOM).rsplit("/abs/", 1)[-1]
        title = " ".join(e.findtext("a:title", namespaces=ATOM).split())
        fname = arxiv_id.replace("/", "_") + ".pdf"
        manifest.append({"file": fname, "arxiv_id": arxiv_id, "title": title})
        path = PDF_DIR / fname
        if not path.exists():
            time.sleep(3)  # arXiv asks for at most 1 request per 3 seconds
            pdf = httpx.get(
                f"https://arxiv.org/pdf/{arxiv_id}", timeout=60, follow_redirects=True
            )
            pdf.raise_for_status()
            path.write_bytes(pdf.content)
            print("saved", fname)
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")


def extract() -> None:
    n_pages = 0
    with PAGES.open("w", encoding="utf-8") as out:
        for pdf in sorted(PDF_DIR.glob("*.pdf")):
            for i, page in enumerate(PdfReader(pdf).pages, start=1):
                text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
                if len(text) < 50:
                    continue
                out.write(
                    json.dumps({"file": pdf.name, "page": i, "text": text}) + "\n"
                )
                n_pages += 1
    print(n_pages, "pages written")


if __name__ == "__main__":
    {"download": download, "extract": extract}[sys.argv[1]]()

import io
import re

from pypdf import PdfReader

MIN_PAGE_CHARS = 50


def safe_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def extract_pages(data: bytes, filename: str) -> list[dict]:
    """Same rules as corpus.py: collapse whitespace, drop pages under 50 chars.
    Raises ValueError for unreadable or encrypted PDFs."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("encrypted PDF")
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
            if len(text) >= MIN_PAGE_CHARS:
                pages.append({"file": filename, "page": i, "text": text})
        return pages
    except ValueError:
        raise
    except Exception as exc:  # pypdf raises many types on bad files
        raise ValueError("unreadable PDF") from exc

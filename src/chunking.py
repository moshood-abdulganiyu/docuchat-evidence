def chunk_page(text: str, size: int, overlap_pct: float) -> list[str]:
    overlap = int(size * overlap_pct)
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # prefer to cut at a sentence end in the last 40% of the window
            cut = text.rfind(". ", start + int(size * 0.6), end)
            if cut != -1:
                end = cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if len(c) >= 50]

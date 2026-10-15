# Decisions
- Demo topic: arXiv papers on RAG and LLM evaluation, 2025-2026
- LLM: Anthropic claude-haiku-5-5 behind src/llm.py
- Embeddings: all-MiniLM-L6-v2 via Hugging Face Inference API (384 dims)
- Vector store: Pinecone serverless, index docuchat, cosine
- Python: 3.12

## Chunking (step 2 experiment)
538 pages from the demo PDFs, page-bounded chunks, sentence-snapping cut in the last 40% of the window.

| size | overlap | chunks | mean len | under 200 chars | mid-sentence ends |
|---|---|---|---|---|---|
| 500 | 10% | 5388 | 425 | 1.9% | 20.0% |
| 800 | 10% | 3332 | 682 | 1.3% | 18.2% |
| 800 | 20% | 3713 | 688 | 0.3% | 17.1% |

Choice: 800 characters, 20% overlap (provisional). Fewest fragments and, once the 538 forced page-end chunks are subtracted, about 2.6% avoidable mid-sentence cuts vs 10% for 500. Costs 11% more chunks than 800/10%. Chunks never cross pages so every citation maps to one page. To confirm with hit rate in step 4 and check MiniLM's 256-token truncation in step 3.

Embeddings: Hugging Face Inference returned 402 and Gemini embeddings hit the 1,000 per day cap, so embeddings now run locally with fastembed.
Chunk size: 500/20%, with the token table (800 = 11.3% over 256 tokens, 700 = 5.9%, 600 = 3.1%, 500 = 1.3%) as the evidence.
# Decisions

Current choices are in the summary. Each entry below says what was decided, why, what it costs, and what would reverse it.

## Summary
- Demo topic: arXiv papers on RAG and LLM evaluation, 2025-2026 (about 30 papers, list in data/manifest.json)
- Embeddings: all-MiniLM-L6-v2 run locally with fastembed (ONNX), 384 dims, normalized
- Vector store: Pinecone serverless, index `docuchat`, cosine, namespace `demo` (6,100 vectors)
- LLM: gemini-2.5-flash behind src/llm.py (step 5)
- Chunking: 500 characters, 20% overlap, page-bounded
- Python 3.12, dependencies with uv

## Embeddings: local fastembed instead of the Hugging Face API
Decision: embed locally with fastembed (Qdrant/all-MiniLM-L6-v2-onnx), cache in data/model_cache.
Reason: Hugging Face Inference returned 402 (no credits). Gemini embeddings hit the free cap of 1,000 requests per day, counted per text, which cannot index 6,100 chunks or serve uploads. One model for demo and uploads.
Cost: onnxruntime and the model file have to fit in the Vercel function. Not yet checked.
Revisit if: the Vercel bundle size or cold start is too large at step 12. Fallback is Pinecone hosted embeddings, which would mean re-indexing.

## Chunking: 500 characters, 20% overlap
Strategy: fixed-size character windows, page-bounded so every citation maps to one page. When a window would end mid-sentence, the cut moves back to the last ". " in the final 40% of the window.

Experiment 1, chunk structure (538 pages):

| size | overlap | chunks | mean len | under 200 chars | mid-sentence ends |
|---|---|---|---|---|---|
| 500 | 10% | 5,388 | 425 | 1.9% | 20.0% |
| 500 | 20% | 6,100 | 427 | 1.2% | 19.4% |
| 800 | 10% | 3,332 | 682 | 1.3% | 18.2% |
| 800 | 20% | 3,713 | 688 | 0.3% | 17.1% |

Page ends account for at most 10.0%, 8.8%, 16.1% and 14.5% of the chunks in the four rows, so avoidable mid-sentence cuts are at least 10.0%, 10.6%, 2.1% and 2.6%. On structure alone 800/20% looked best, and it was chosen provisionally.

Experiment 2, MiniLM reads at most 256 tokens (20% overlap):

| size | chunks | mean tokens | 95th percentile | over 256 tokens |
|---|---|---|---|---|
| 500 | 6,100 | 113 | 191 | 1.3% |
| 600 | 5,039 | 136 | 226 | 3.1% |
| 700 | 4,256 | 159 | 265 | 5.9% |
| 800 | 3,713 | 181 | 299 | 11.3% |

Decision: 500/20%, the largest size under the 3% gate. 800 fails at 11.3% and 700 at 5.9%.
Cost: 6,100 vectors instead of 3,713, and at least 10.6% avoidable mid-sentence cuts against at least 2.6% for 800/20%.
Revisit if: step 7 traces retrieval failures to chunk size, or the question set grows past about 50.

## Step 4: gold pages from answer strings; 600/20% comparison skipped
Decision: a question's gold pages are all pages of the gold paper that contain its answer string (`answer_patterns` in eval/questions.jsonl), not the single page I picked. 500/20% stays, and the 600/20% comparison was not run.
Reason: the first run scored 11/18 at k=5 with file+page, but five of the misses returned a page that stated the same fact. With 18 questions, one question is 5.6 points, too coarse to separate 500 from 600.
Result: 10/18 (k=3) and 11/18 (k=5) before the fix, 15/18 and 16/18 after. File-only hit rate is 17/18 in both.
Cost: relabelling after seeing results can only raise the score. Both sets of numbers are kept in the README.
Revisit if: the question set grows, or step 7 shows chunk size matters.

## LLM: gemini-2.5-flash
Decision: gemini-2.5-flash for both RAG and the no-retrieval baseline, behind one module, src/llm.py.
Reason: free tier, and one file to change if the provider changes.
Cost: Google may use free-tier inputs to improve its products. The upload box and README will say that uploaded text is sent to Google.
Revisit if: free-tier rate limits (not yet checked) block the evaluation runs.
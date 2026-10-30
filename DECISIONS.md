# Decisions

Current choices are in the summary. Each entry below says what was decided, why, what it costs, and what would reverse it.

## Summary
- Demo topic: arXiv papers on RAG and LLM evaluation, 2025-2026 (about 30 papers, list in data/manifest.json)
- Embeddings: all-MiniLM-L6-v2 run locally with fastembed (ONNX), 384 dims, normalized
- Vector store: Pinecone serverless, index `docuchat`, cosine, namespace `demo` (6,100 vectors)
- LLM: gemini-3.5-flash-lite behind src/llm.py, temperature 0
- Chunking: 500 characters, 20% overlap, page-bounded
- Citations: the model cites passage numbers, code maps them to file and page
- Evaluation: 17 questions, answers scored correct, abstained or wrong, retrieval reported separately
- Python 3.12, dependencies with uv
- Sessions: `sess_<unix_timestamp>_<16 hex>` namespaces, strict regex, isolation by namespace only
- Upload limits: 1 file per request, 4 MB, 5 files per session, 800 chunks per file
- Chat history: browser sends up to 20 messages, server keeps the last 6, follow-ups rewritten with the same model
- Frontend: plain HTML, CSS and JavaScript in `public/`, no framework, light and dark themes
- Logs: JSON events for requests, queries and query errors, counts and timings only, no text

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
Revisit if: step 7 traces retrieval failures to chunk size, or the question set grows past about 50. Step 6 found one question (q13) where the right page was returned but no chunk held the answer, which is a small sign that chunk boundaries matter. One case is not enough to change the size.

## Step 4: gold pages from answer strings; 600/20% comparison skipped
Decision: a question's gold pages are all pages of the gold paper that contain its answer string (`answer_patterns` in eval/questions.jsonl), not the single page I picked. 500/20% stays, and the 600/20% comparison was not run.
Reason: the first run scored 11/18 at k=5 with file+page, but five of the misses returned a page that stated the same fact. With 18 questions, one question is 5.6 points, too coarse to separate 500 from 600.
Result: 10/18 (k=3) and 11/18 (k=5) before the fix, 15/18 and 16/18 after. File-only hit rate is 17/18 in both.
Cost: relabelling after seeing results can only raise the score. Both sets of numbers are kept in the README.
Revisit if: the question set grows, or step 7 shows chunk size matters.

## LLM: gemini-3.5-flash-lite
Decision: gemini-3.5-flash-lite for both RAG and the no-retrieval baseline, behind one module, src/llm.py, at temperature 0.
Reason: free tier, and one file to change if the provider changes. The first choice, gemini-2.5-flash, returned 404 on 2026-10-15 ("no longer available to new users"). gemini-3.8-flash was the suggested replacement, but its free quota is reported at about 20 requests per day, and the evaluation needs 36 or more calls (18 baseline, 18 RAG, plus reruns). The free quota of gemini-3.5-flash-lite was not confirmed in the AI Studio dashboard.
Cost: a small model. A larger model may know more without retrieval, so the baseline comparison applies to this model only. Google may use free-tier inputs to improve its products. The upload box and README will say that uploaded text is sent to Google.
Revisit if: free-tier rate limits block the evaluation runs, or the model is retired.

## RAG: citations by passage number, score gate at 0.2
Decision: the prompt numbers the retrieved chunks [1] to [5], the model cites those numbers, and the code maps each number to a file and page (one entry per distinct page). If no chunk scores at least `MIN_SCORE` (0.2), the model is not called. Otherwise the model must reply exactly `NOT_FOUND` when the passages do not contain the answer. Each result records a `reason` (gate, model or empty).
Reason: a model that cites numbers cannot invent a file name or page. The gate saves quota on questions with no relevant chunk at all.
Result: the gate filtered none of the 18 evaluation questions, and not the off-topic test question either (its top scores were 0.247 to 0.290). All 6 refusals in the evaluation came from the model.
Cost: `MIN_SCORE` is a guess and is uncalibrated. A citation shows which chunk the model used, not that the chunk supports the claim.
Revisit if: a calibration on more off-topic and in-domain questions shows a threshold that separates them, which the observed gap between 0.29 and about 0.49 suggests but one test does not prove.

## Evaluation: 17 questions, three outcomes, gold page as citation check
Decision: score answers as correct, abstained or wrong, on 17 questions with q05 excluded. Report retrieval hit rate (18 questions, step 4) in a separate row from answer correctness. Count a citation as good when the cited page is the gold page, the page the question was written from.
Reason: the baseline says "I do not know." on most questions, and a "wrong" count would punish that unfairly. q05 is ambiguous (five values in the paper's table row for the 8B Llama model), and rewording it would have meant rerunning both systems. Checking every claim against its cited page by hand for all rows was too slow for this stage.
Result: baseline 0 correct, 16 abstained, 1 wrong. RAG 11 correct, 6 abstained, 0 wrong. Citation on the gold page: 11 of 11 answered rows. 2 of the 11 answered rows were scored automatically from the gold string, 9 by hand.
Cost: the citation measure is weaker than a claim-level check. The baseline comparison shows that retrieval lets the model answer papers it cannot know, not that retrieval beats a model that already knows the topic. 17 questions, so one question is 5.9 points. One person wrote the questions and scored the answers.
Revisit if: the question set grows, an independent scorer is available, or questions are added on topics a model without retrieval could plausibly know.


## Step 8: query API

**Namespace is not a request field.** The server pins `/query` to `demo`. A public field would let any caller read any namespace, including other people's uploads once step 9 exists. Step 9 adds a validated `session_id` instead. Cost: no way to query another namespace for testing without a code change.

**`/query` is a plain `def`, not `async def`.** `rag_answer` blocks on Pinecone, Gemini and retry sleeps. FastAPI runs a plain `def` in a worker thread, so one slow request does not stop others. Cost: thread-pool limits apply under load.

**Error mapping by status code, generic messages.** 429 becomes 503 (try again later), everything else becomes 502. The client never sees exception text, which could contain keys or internals. The full exception is logged. Cost: the client cannot tell a Pinecone failure from a Gemini failure.

**Fixed input limits.** Question 1 to 500 characters, k 1 to 10. They bound cost per request. The numbers are not measured.

**Tests fake `rag_answer`.** The 12 API tests run with no network and no keys, so they are fast (about 4 s) and safe for CI. They cannot catch retrieval or LLM regressions. Those stay with the eval scripts.

**Entry point `api/index.py`.** It re-exports `app`, because current Vercel docs detect a FastAPI instance named `app`. Alternative: `tool.vercel.entrypoint` in `pyproject.toml`. To be confirmed on a preview deploy in step 12, including whether paths get an `/api` prefix.

**Lint policy.** `SIM115` is ignored for `eval/**` only (short scripts that exit after reading). `B023` in `eval/auto_score.py` was fixed by binding `pats` as a default argument. Formatting changes to 26 files went in a separate commit so the step 8 diff stays readable.


## Steps 9 to 12: uploads, chat, frontend, deployment

Date of the deployment decisions: 2026-10-29. Append this block to the end of DECISIONS.md.

### Session ids and namespaces
**Decision.** A session is a Pinecone namespace named `sess_<10-digit unix time>_<16 hex>`. The server creates it on the first upload and returns it. The browser keeps it in sessionStorage. Every query is routed to `session_id` or, if absent, to `demo`. A strict regex validates the id, and `demo` is rejected as a session id.
**Why.** The timestamp lets the cleanup job read a session's age from its name with no database. The strict regex means a caller cannot pick another namespace by sending a crafted value.
**Cost.** The id is the only access control. Anyone holding it can query and upload to that session.

### Upload limits and check order
**Decision.** One file per request, 4 MiB, 5 files per session, 800 chunks per file. Checks run in this order: `.pdf` name, bounded read (413), `%PDF` header, session id (422), duplicate name or 5 files (409), parse (422, includes scanned and encrypted PDFs), chunk cap (422), index (502).
**Why.** Cheap checks run before the expensive ones. The 800-chunk cap is a guess, not a measurement.

### Overlap passed as a fraction
**Decision.** `chunk_page` takes overlap as a fraction (0.20). Passing 20 produced 3,439 chunks for one file, so upload indexing now uses `OVERLAP_PCT = 0.20`.
**Why.** Found during step 9. `index_corpus.py` still has its own loop and constants and has not been moved onto `index_pages`.

### Follow-up rewriting
**Decision.** `rewrite_question(question, history)` makes one Gemini call, only when history exists. The browser sends the last 6 messages, and the server truncates to the last 6 again. If the rewrite call fails, the original question is used. The response carries `rewritten_question` and the UI shows it as "Searched as".
**Why.** Retrieval needs a standalone question. A failed rewrite should degrade to a normal query, not an error.
**Cost.** One extra Gemini call per follow-up. Rewrite quality is not measured.

### Frontend without a framework
**Decision.** Static HTML, CSS and JS in `public/`. Answers are rendered with `textContent`, uploads use XHR for progress, mic uses the Web Speech API, read-aloud uses speechSynthesis.
**Why.** One page, no build step, and the build guide said to pick one approach and not mix frameworks. `textContent` avoids injecting model output as HTML.
**Cost.** Mic works only in Chrome and Edge. Not tested on mobile.

### Frontend restyle with light and dark themes
**Decision.** `index.html`, `style.css` and `app.js` were restyled with a light and a dark theme. A header button switches them, the choice is saved in the browser, and a first visit follows the system setting. Element IDs, API calls, upload logic and chat logic were not changed.
**Why.** The first version was plain. The README screenshots are taken in both themes.
**Cost.** The restyle was checked for JavaScript syntax errors, then in a browser on the live site. Not tested on mobile. Animations turn off when the visitor has reduced motion set.

### Vercel entrypoint
**Decision.** `src/app.py` is the entrypoint, found by Vercel automatically. `api/index.py` was deleted. `public/` is served by the CDN, so the `StaticFiles` mount runs only when the `VERCEL` environment variable is unset.
**Why.** The Vercel FastAPI docs list `src/app.py` as a recognized entrypoint and say a manual static mount is not needed. Two entrypoints risked a conflict.

### Embedding model downloaded to /tmp, not bundled
**Decision.** On Vercel the model downloads into `/tmp/model_cache` on the first request after a cold start. `_cache_dir()` uses `MODEL_CACHE_DIR` if set, else `data/model_cache` if writable, else the system temp directory. Vercel env vars: `MODEL_CACHE_DIR=/tmp/model_cache`, `HF_HOME=/tmp/hf`.
**Why.** The deploy folder is read-only and `data/model_cache` is gitignored. The first deploy failed with "Read-only file system" in the Vercel log. The model is 91,104,077 bytes across 9 files (about 87 MiB), which would fit in the repo, but committing it was not needed to make the deploy work.
**Cost.** The first request after a cold start is slow. The time was not measured. If it is too slow, bundle the model.
**What I got wrong first.** The first fix relied on the `VERCEL` variable to pick the path, and the deploy still failed. The second version checks whether the folder is writable.

### Reading Pinecone list results
**Decision.** `list_session_files` reads `getattr(vid, "id", vid)`.
**Why.** The Pinecone SDK returns objects with an `.id` attribute, not strings. The fourth upload failed in every session with `AttributeError: 'ListItem' object has no attribute 'rsplit'`. The earlier tests replaced the whole function with a fake, so the real code never ran. `tests/test_indexing_list.py` now runs the real function against a fake index that returns objects with `.id`.

### MIN_SCORE lowered from 0.2 to 0.10
**Decision.** The score gate is 0.10.
**Why.** A short CV PDF scored 0.16 to 0.32 on its own questions, and the best chunk for a leadership question scored 0.198, so the 0.2 gate dropped every chunk and returned "Not found" although the answer was in the file. The off-topic jollof rice question scored 0.247 to 0.290 against the arXiv papers, so the gate could not separate on-topic from off-topic anyway. The model's `NOT_FOUND` reply is the real guard against answering from outside the chunks. The 18 evaluation questions scored 0.49 to 0.73 and were never gated, so step 7 results do not change.
**Cost.** Questions the old gate blocked now cost one Gemini call. 0.10 is a guess based on one short document and is not calibrated.

### Partial answers allowed in the RAG prompt
**Decision.** Rule 3 of the system prompt now says: if the passages answer only part of the question, answer that part with citations and add one sentence naming what the passages do not state; never guess the missing part. `NOT_FOUND` is only for no answer to any part.
**Why.** "What is the graduation date and the final grade?" refused with `reason: "model"` although the CGPA chunk was among the 5 retrieved chunks (the question "What is the CGPA?" returned `4.59/5.00 [1]`). After the change the answer cited the grade and said the date is not stated. Checked live on one document.
**What it may explain.** Some of the three unexplained step 6 refusals (q03, q07, q16) may have the same cause. Not checked.
**Effect on results.** The step 7 table was produced with the old prompt and the old gate. The README says so. Rerunning `eval/rag_answers.py` and rescoring would update it.

### Cleanup job
**Decision.** `GET /api/cron/cleanup`, triggered by Vercel Cron daily at 03:00 UTC (`0 3 * * *`). It lists namespaces from `describe_index_stats()`, keeps only names matching the strict session regex, and deletes those older than 24 hours. The route requires `Authorization: Bearer <CRON_SECRET>` and compares with `hmac.compare_digest`. With no `CRON_SECRET` set it rejects every request.
**Why.** The session regex never matches `demo`, so `demo` cannot be deleted. Reading age from the name needs no database.
**Cost.** A daily schedule means a session can live up to about 48 hours. A third-party page says Hobby cron runs once a day. I did not confirm that in the Vercel docs.
**Verified.** 401 without the header, 200 with it, a fake 2001 namespace deleted, `demo` kept.

### CI
**Decision.** One GitHub Actions job on pushes to main and on pull requests: `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest -q`, Python 3.12.
**Why.** The same three checks I run locally, one per line, because a chained command once let a failing check pass.

### No per-IP rate limit, no namespace cap for now
**Decision.** Neither is built. Both are listed as known limits.
**Why.** A Vercel function keeps no state between calls, so a real limiter needs extra storage. The Pinecone free plan allows 100 namespaces per index and `demo` uses one, so a burst of about 99 new sessions in one day could block uploads until the next cleanup. A namespace cap in `/upload` is the cheap next step.
**Cost.** Anyone with the URL can use the Gemini free quota.

### Structured logs
**Decision.** Three JSON events through `src/logs.py`. `request` for every `/query` and `/upload` call (path, status, ms). `query` for each answered question (mode, found, reason, k, retrieved, top_score, cited, uncited, rewritten, rewrite_ms, rag_ms). `query_error` for each failure (mode, error_type, error_code). Question text, answer text, file names and session ids are never logged.
**Why.** Uploads are private, and the session id is the only access control, so it stays out of the logs too. Timings are split so the cost of the follow-up rewrite is visible. `tests/test_query_logging.py` checks that the question and answer text do not appear in the events.
**What it showed.** Four demo questions took 1,385 to 2,494 ms end to end. In one follow-up the rewrite took 604 ms and retrieval plus the answer took 853 ms.
**Cost.** Four samples, and which requests were cold starts was not recorded. Cold-start time is still not measured. The error log does not keep the exception message, only its class name, so a new failure may need the full traceback in the Vercel log.

### Limits checked against current docs on 2026-10-29
- Vercel: request and response body 4.5 MB, so the 4 MiB upload limit stays. Python function bundle 500 MB uncompressed. FastAPI apps run as one function on Fluid compute by default. A third-party page reports 300 s default and maximum duration on Hobby, which I did not confirm in the dashboard. Cron runs on production deployments only.
- Pinecone Starter: 100 namespaces per serverless index, 2 GB storage, 2M write units and 1M read units per month.
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

LLM-**assisted** review tooling for **PyCon TW 2025** talk proposals. The pipeline pulls proposals from Metabase, asks an LLM to produce *suggested* reviews/categories/diffs, and compares those suggestions against the actual human reviewer record. All user-facing review text is **Traditional Chinese** (`*_tc`) with optional English translations (`*_en`).

> **Critical positioning — read before suggesting features:**
> The LLM is an **auxiliary suggestion tool for human reviewers**, not an automated reviewer. Every binding accept/reject decision is made by a human; LLM output is reference material only. Concretely:
> - `review` produces suggested votes/comments **for a human to consider**, not to merge into the review record.
> - `evaluate` measures how well LLM suggestions align with human judgment (calibration), it is **not** grading humans against an LLM ground truth.
> - `diff` helps human reviewers spot what changed between stages so they don't re-read everything.
> - Human reviews live in Metabase's `reviews_review` table; LLM outputs live only in `output/*.xlsx`. **These two stores must stay separate** — never propose a flow that writes LLM output back into the review record.
>
> The codebase is ambiguous on this because `ProposalReview.vote` outputs the same `+1/+0/-0/-1` literals humans use (`src/models.py:8`). Don't be misled — they are *suggested* votes.

Data flows: Metabase (DB id `12` for pycontw-2025) → `pycontw_2025_proposals_<DATE>.xlsx` → LLM review/translate/evaluate → `output/*.xlsx` (human reviewers consume this as reference, then vote in Metabase themselves).

## Common commands

There is no `requirements.txt` checked in. Dependencies in use: `openai`, `langchain-openai`, `langchain-google-genai`, `pandas`, `openpyxl`, `pydantic`, `aiohttp`, `python-dotenv`, `requests`.

`.env` must define at minimum `OPENAI_API_KEY` and (for DB pulls) `METABASE_URL`, `METABASE_USERNAME`, `METABASE_PASSWORD`.

```bash
# Pull 2025 proposals from Metabase
python3 src/get_2025_proposals.py

# Run LLM review on a proposal file (use --limit N when iterating)
python3 run_llm.py review \
  --proposal_file data/pycontw_2025_proposals_20250520.xlsx \
  --model o4-mini --reasoning_effort high --with_translation

# Compare LLM reviews against human reviews
python3 run_llm.py evaluate \
  --llm_reviews_file output/llm_review_o3-mini_20250404.xlsx \
  --human_reviews_file data/db_merged_fixed/reviews_20250404.xlsx \
  --model o3-mini --reasoning_effort high

# Categorize proposals
python3 run_categorize.py --proposal_file <xlsx> --model o4-mini --reasoning_effort high

# Diff two snapshots of proposals
python3 run_proposal_diff.py \
  --stage1_file data/pycontw_2025_proposals_snapshot_20250427.xlsx \
  --stage2_file data/pycontw_2025_proposals_20250520.xlsx \
  --model o4-mini --reasoning_effort high
```

There is no test suite (`.pytest_cache/` exists from past runs but no `tests/`). To smoke-test code paths, always pass `--limit 3` to keep API spend small.

`run_llm.py` forces `OPENAI_TEMPERATURE=0` at startup; do not rely on temperature for variability.

## Architecture: how the pieces connect

### Two parallel CLI entry points

There are two competing top-level entry shapes — be aware which you are touching:

1. **`run_llm.py`** — bootstraps `src/` onto `sys.path`, then dispatches to `src/main_llm.py:main()`. Subcommands: `review`, `evaluate`, `both`, `diff`.
2. **`run_categorize.py`** and **`run_proposal_diff.py`** — separate scripts at the repo root that import `src.llm.*` directly. `run_proposal_diff.py` overlaps with `run_llm.py diff` (both call `run_proposal_diff_analysis_sync`); changes to diff behavior need to be checked against both.

### Two-flavored Python imports — known footgun

`run_llm.py` inserts `src/` into `sys.path` so its handlers import as `from llm.review import ...` (no `src.` prefix). But files inside `src/` itself use the `from src.X import Y` form (e.g. `src/llm/review.py`, `src/evaluation/evaluator.py`, `src/get_2025_proposals.py` — the last two also do their own `sys.path.insert`). Both styles happen to resolve because the project root is also on `sys.path` at runtime. **When adding a new module under `src/`, mirror the surrounding file's import style** rather than mixing them in one file.

### Async pipeline (`src/llm/review.py`)

`run_llm_review` is a sync wrapper around `run_llm_review_async`. The async core:

1. `load_proposal_data` reads the proposal Excel with `dtype={'proposal_id': str}` — **`proposal_id` must stay a string at all times** to avoid Excel int overflow on large IDs. `save_results` re-casts to `str` defensively.
2. `setup_llm_chain` builds a LangChain `PromptTemplate | structured_llm` pipeline. The model branch picks the LLM class:
   - `gemini-*` → `ChatGoogleGenerativeAI`
   - `gpt-4o-mini` → `ChatOpenAI(temperature=0)`
   - `o3*` / `o4*` → `ChatOpenAI(reasoning_effort="high")` (no temperature param — these models reject it)
3. Output schema is enforced via `llm.with_structured_output(EnhancedProposalReview)` (or `ProposalReview` when `--with_translation` is off). Pydantic models live in `src/models.py`.
4. `process_proposals_async` fans out one task per proposal via `asyncio.gather(...)` — **no batching**. If you hit OpenAI rate limits, lower `--limit` or add chunking here.
5. Translation runs as a second `asyncio.gather` after reviews complete, using a separate chain (`gpt-4o-mini`, `prompt/translation_prompt.txt`). Each translated field becomes `<field>_en`.

### LLM client (`src/llm/client.py`)

`OpenAIClient` is the lower-level client used by `proposal_diff.py` and `evaluator.py` (the `review.py` flow uses LangChain instead). Same model-family branching applies inside `_generate_chat_completion`. Has a `retry_with_exponential_backoff` helper and an `aclose()` that swallows httpx shutdown noise — leave the warning suppression in place; it is intentional.

### Data layer (`src/db/`)

`MetabaseConnector` authenticates against Metabase (`/api/session`), then runs SQL templated with `{{param}}` placeholders. Queries live in `src/db/queries.py`. The `negative proposals` query is the canonical "find weak proposals to send to the LLM" filter (≥25% negative votes, ≥3 reviews, abstract not empty/test). Raw SQL prototypes are in the top-level `pycon_llm_sql` file.

### Prompts (`prompt/`)

Plain-text templates with `{VAR}`-style placeholders. `full_prompt.txt` is the production review prompt; `simple_prompt.txt` is a stripped-down baseline. Other prompts: `evaluation_prompt.txt`, `categorization_prompt.txt`, `translation_prompt.txt`, `proposal_diff_prompt.txt`. All must produce JSON matching the corresponding Pydantic model in `src/models.py`.

### Evaluation (`src/evaluation/evaluator.py`)

Joins LLM reviews with human reviews on `proposal_id`, computes `llm_human_vote_diff` and `llm_agreement_pct`, and asks the LLM to qualitatively grade its own outputs against the human consensus. `run_llm.py both` chains review → evaluate using a fresh `asyncio` event loop for the evaluate stage to dodge "Event loop is closed" errors when both stages run in one process.

## Conventions specific to this repo

- **All output is `.xlsx` named `<purpose>_<model>_<YYYYMMDD>.xlsx`** under `output/` (or `data/` for snapshots).
- **`proposal_id` is always a string** in DataFrames and Excel; never let pandas infer it as int.
- Vote literals are exactly `+1`, `+0`, `-0`, `-1` (defined in `ProposalReview`). Don't introduce new vote symbols.
- Field naming: `*_tc` (Traditional Chinese) and `*_en` (English) — keep both in sync when adding new review fields.
- Logs go to `logs/<task>_<YYYYMMDD>.log` (auto-created); don't print to stdout for long runs.
- `data/`, `output/`, `logs/`, `archive/`, `.history/`, `exp/` are gitignored. The `data/db_merged_fixed/` directory holds canonical 2024 ground-truth files used during evaluation.
- Per `.cursor/rules/`, ignore `.history/` and `data/archive/` when reading the codebase.
- Scripts noted as broken in the README and not to rely on: `pycon_api_client.py`, `notebook_api_example.py`, `api_test.py`, `simple_api_example.py`.

## When changing model handling

The model-family branch (gemini / gpt- / o3|o4) appears in **two places**: `setup_llm_chain` in `src/llm/review.py` and `_generate_chat_completion` in `src/llm/client.py`. A new model family needs both edits. The reasoning-effort flag is OpenAI-`o`-series only; gpt-4o family takes `temperature` instead.

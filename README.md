# Enterprise RAG Document Assistant

Answer questions about German PDF documents with citations down to the document
and page level — and measure whether those citations are actually right.

> **Status: phase 0 (setup).** The full README, with the architecture diagram
> and the evaluation results table, is written once the harness in phase 5 has
> produced numbers. See [rag-assistant-roadmap.md](rag-assistant-roadmap.md).

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync --all-groups          # install dependencies
cp .env.example .env          # then fill in ANTHROPIC_API_KEY
uv run uvicorn app.main:app --reload
```

Verify: <http://localhost:8000/health>

## Development

```bash
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mypy app/              # typecheck
uv run pre-commit install     # install the git hook (once)
```

Qdrant (needed from phase 2 onwards):

```bash
docker compose up -d qdrant
```

## Project layout

```
app/
├── api/          FastAPI routers — thin: validate, delegate, serialize
├── ingestion/    PDF -> chunks
├── retrieval/    vector, BM25, hybrid, rerank
├── generation/   prompting, LLM client
├── agent/        tool layer
├── evaluation/   evaluation harness
├── config.py     pydantic settings
└── models.py     core schemas
ui/               Streamlit frontend (talks to the API over HTTP only)
eval/
├── dataset/      questions.jsonl
└── results/      ablation reports
configs/          named experiment configurations
```

## Design notes

Two decisions are load-bearing and easy to get wrong; both are enforced by
tests in `tests/test_models.py` and documented in
[CLAUDE.md](CLAUDE.md#invarianten-nicht-verhandelbar).

**Gold labels are character spans, not chunk IDs.** Phase 5 varies chunk size,
which changes every chunk ID. An evaluation set keyed on chunk IDs would be
silently invalidated by the first ablation — the exact experiment the project
exists to run. `Recall@K` therefore asks whether any retrieved chunk *overlaps*
the gold span in the source document.

**Page numbers are a list.** Chunks straddle page boundaries. The page citation
is the product's headline feature, so a chunk that loses it during chunking is
worse than no chunk at all.

## Limitations

- **Tables** are extracted as flowing text. In annual reports and standards —
  the intended document types — many interesting questions target tables
  specifically.
- **Scanned PDFs** are not supported. There is no OCR step; documents need a
  text layer.

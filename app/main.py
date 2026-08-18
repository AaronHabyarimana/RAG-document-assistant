"""Application startup. No business logic lives here — only wiring."""

from fastapi import FastAPI

from app.api import health

app = FastAPI(
    title="RAG Document Assistant",
    description="Answer questions about uploaded PDFs, with document and page citations.",
    version="0.1.0",
)

app.include_router(health.router)

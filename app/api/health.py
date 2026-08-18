"""Liveness endpoint."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


@router.get("/health")
async def health() -> HealthResponse:
    """Report that the service is up."""
    return HealthResponse(status="ok", version="0.1.0")

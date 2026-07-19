from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import qa, upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title="Medical Report Intelligence Platform",
    description=(
        "Upload medical reports (PDFs/images), extract structured data via OCR and LLM, "
        "ask grounded questions with source citations, and track trends over time."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Streamlit frontend runs on localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(qa.router)


@app.on_event("startup")
async def _create_data_dirs():
    """Ensure required data directories exist at startup."""
    for d in ["./data", "./data/chroma", "./backend/data/synthetic_reports"]:
        Path(d).mkdir(parents=True, exist_ok=True)


@app.get("/health", tags=["system"])
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}



if __name__ == "__main__":
    import uvicorn
    from backend.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False,
    )

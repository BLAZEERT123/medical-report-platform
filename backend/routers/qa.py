"""
Q&A Router — POST /ask
Accepts a user question and returns retrieved chunks (for the Retrieval Inspector)
plus the LLM-generated cited answer.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.models.report import QAResponse
from backend.services import chroma_service, qa_service

router = APIRouter(prefix="/qa", tags=["qa"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender: 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    chat_history: list[ChatMessage] = Field(default_factory=list, description="Previous conversation history")


@router.post("/ask", response_model=QAResponse)
async def ask_question(body: QuestionRequest):
    """
    Answer a patient question using hybrid retrieval from:
    - Store A: user's own uploaded reports
    - Store B: reference medical corpus (MedlinePlus / WHO / CDC)

    Returns the retrieved chunks (Retrieval Inspector) AND the cited answer.
    """
    try:
        response = qa_service.answer_question(body.question, body.chat_history)
        return response
    except Exception as exc:
        err = str(exc)
        # Give the user a readable message for common failures
        if "503" in err or "504" in err or "Deadline" in err or "unavailable" in err.lower():
            raise HTTPException(
                status_code=503,
                detail="The AI embedding service is temporarily unavailable. Please wait a few seconds and try again.",
            )
        raise HTTPException(status_code=500, detail=f"Q&A failed: {exc}")


@router.get("/store-stats")
async def store_stats():
    """Return document counts for both Chroma collections."""
    return chroma_service.get_store_stats()

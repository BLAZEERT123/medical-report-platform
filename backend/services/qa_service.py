"""
Q&A Service — Hybrid retrieval + LLM answer generation.

Flow:
  1. If chat history exists, rewrite the follow-up question to be standalone
     (inspired by Ratnesh-181998/Medical-RAG-Chatbot's context-aware query technique)
  2. Retrieve from Store A (user reports) AND Store B (reference corpus)
  3. Return both chunk lists to caller BEFORE generating answer (Retrieval Inspector)
  4. Merge context and generate a cited answer
  5. Score confidence based on retrieved context quality
  6. NEVER refuse if reference chunks exist — always give a useful medical answer
     grounded in both the report data and general medical knowledge
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from backend.models.report import QAResponse, RetrievedChunk, SourceCitation
from backend.services import chroma_service
from backend.services.llm_factory import get_llm

logger = logging.getLogger(__name__)

# ── Conversation window size (inspired by Medical-RAG-Chatbot memory pattern) ─
_MEMORY_WINDOW_K = 5   # keep last 5 Q&A pairs in context


# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a knowledgeable, empathetic medical assistant helping a patient understand
their lab results and general health questions.

RULES:
1. Always provide a genuinely helpful, informative answer.
2. If the patient's report data is available in the context, reference their actual values
   explicitly (e.g. "Your platelet count is 85,000/μL, which is below the normal range
   of 150,000–400,000/μL").
3. If no report data is available for the specific question, answer using your general
   medical knowledge — explain what the parameter measures, why it might be abnormal,
   common causes, and what a doctor typically recommends.
4. Be scientifically accurate but use plain language — explain any medical term you use.
5. Cite sources inline as [Source: <name>] when using retrieved context. Indicate if it's from their report or a reference.
6. Be empathetic — the patient may be worried.
7. End every answer with: "⚕️ IMPORTANT: This is an AI analysis, not a medical diagnosis. Always consult your doctor or healthcare provider for medical advice."
8. NEVER say "I don't have enough information" or refuse to answer — always provide
   educational medical context even if the specific report data is missing.
"""

_HUMAN_PROMPT = """\
Patient Question: {question}

--- CONTEXT FROM PATIENT'S OWN REPORTS (Store A) ---
{report_context}

--- CONTEXT FROM REFERENCE MEDICAL SOURCES (Store B) ---
{reference_context}

Answer the patient's question thoroughly. Reference their actual report values where
available. If report data is limited, use general medical knowledge to educate them.
"""

# ── Query rewriting prompt (standalone question for follow-up Qs) ─────────────
# Inspired by Ratnesh-181998/Medical-RAG-Chatbot's context-aware chain technique

_REWRITE_SYSTEM = """\
You are a query reformulation assistant for a medical chatbot.
Given a conversation history and a follow-up question, rewrite the follow-up question
to be fully self-contained and understandable without the conversation history.
Keep the rewritten question concise (≤ 30 words). Output ONLY the rewritten question, no preamble.
If the question is already standalone (no pronoun references to prior context), return it unchanged.
"""

_REWRITE_HUMAN = """\
Conversation History:
{history_text}

Follow-up Question: {question}

Rewritten standalone question:"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_chunks(chunks: List[RetrievedChunk]) -> str:
    if not chunks:
        return "No specific data retrieved from this source."
    parts = []
    for c in chunks:
        parts.append(f"[{c.source_name}]\n{c.snippet}")
    return "\n\n".join(parts)


def _window_history(chat_history: List, k: int) -> List:
    """Keep only the last k Q&A pairs (2*k messages) from history."""
    if len(chat_history) <= k * 2:
        return chat_history
    return chat_history[-(k * 2):]


def _build_lc_messages(chat_history: List) -> List:
    """Convert chat_history dicts to LangChain message objects."""
    messages = []
    for msg in chat_history:
        if hasattr(msg, 'role'):
            role, content = msg.role, msg.content
        else:
            role, content = msg.get("role"), msg.get("content", "")

        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def _rewrite_query(question: str, chat_history: List) -> Optional[str]:
    """
    Rewrite a follow-up question to be standalone.
    Returns the rewritten question string, or None if no rewrite needed/possible.
    Inspired by the context-aware chaining in Ratnesh-181998/Medical-RAG-Chatbot.
    """
    if not chat_history:
        return None  # First question — no history, no rewriting needed

    # Build history text summary (last 3 exchanges max)
    recent = _window_history(chat_history, k=3)
    history_lines = []
    for msg in recent:
        role = msg.role if hasattr(msg, 'role') else msg.get("role")
        content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
        prefix = "User" if role == "user" else "Assistant"
        history_lines.append(f"{prefix}: {content[:200]}")
    history_text = "\n".join(history_lines)

    # Check if question has follow-up pronouns/references — if not, skip rewriting
    followup_signals = {"it", "this", "that", "they", "these", "those", "the result",
                        "the value", "my result", "my value", "what about", "and what",
                        "why does", "does that", "is it", "what does", "mean", "can you"}
    q_lower = question.lower()
    needs_rewrite = any(sig in q_lower for sig in followup_signals)
    if not needs_rewrite:
        return None

    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", _REWRITE_SYSTEM),
            ("human", _REWRITE_HUMAN),
        ])
        response = (prompt | llm).invoke({
            "history_text": history_text,
            "question": question,
        })
        rewritten = response.content.strip()
        if rewritten and rewritten.lower() != question.lower():
            logger.info("Query rewritten: '%s' → '%s'", question[:80], rewritten[:80])
            return rewritten
    except Exception as exc:
        logger.warning("Query rewriting failed (%s) — using original question", exc)

    return None


def _score_confidence(
    report_chunks: List[RetrievedChunk],
    reference_chunks: List[RetrievedChunk],
) -> str:
    """
    Score answer confidence based on retrieved context quality.
    Inspired by source attribution in Ratnesh-181998/Medical-RAG-Chatbot.
    - High:   at least 1 report chunk with score > 0.7
    - Medium: some context retrieved (any score)
    - Low:    no context at all
    """
    all_chunks = report_chunks + reference_chunks
    if not all_chunks:
        return "Low"

    top_score = max(c.score for c in all_chunks)
    has_report = len(report_chunks) > 0

    if has_report and top_score >= 0.55:
        return "High"
    elif top_score >= 0.35 or len(all_chunks) >= 2:
        return "Medium"
    else:
        return "Low"


def _build_citations(
    report_chunks: List[RetrievedChunk],
    reference_chunks: List[RetrievedChunk],
) -> List[SourceCitation]:
    """
    Build structured SourceCitation list from retrieved chunks.
    Deduplicates by source_name, keeps top-scored entry per source.
    Inspired by source attribution UI in Ratnesh-181998/Medical-RAG-Chatbot.
    """
    seen: dict[str, SourceCitation] = {}
    for chunk in sorted(report_chunks + reference_chunks, key=lambda c: c.score, reverse=True):
        key = chunk.source_name
        if key not in seen:
            seen[key] = SourceCitation(
                title=chunk.source_name,
                url=chunk.source_url,
                snippet=chunk.snippet[:300],
                score=chunk.score,
                source_type=chunk.source_type,
            )
    return list(seen.values())[:6]  # cap at 6 citations


# ── Main entry point ──────────────────────────────────────────────────────────

def answer_question(question: str, chat_history: List = None) -> QAResponse:
    """
    Main entry point for the Q&A feature.

    Enhancements over original:
    - Query rewriting for follow-up questions (standalone retrieval queries)
    - ConversationBufferWindowMemory pattern (window k=5)
    - Confidence scoring (High/Medium/Low)
    - Structured source citations
    - End-to-end latency tracking
    """
    t_start = time.monotonic()
    logger.info("Q&A question: '%s'", question[:100])

    if chat_history is None:
        chat_history = []

    # ── Window the history (keep last 5 pairs = 10 messages) ─────────────────
    windowed_history = _window_history(chat_history, k=_MEMORY_WINDOW_K)

    # ── Step 1: Query rewriting for follow-up questions ───────────────────────
    rewritten_query = _rewrite_query(question, windowed_history)
    retrieval_query = rewritten_query if rewritten_query else question

    # ── Step 2: Retrieve from both stores ────────────────────────────────────
    report_chunks = chroma_service.retrieve_from_reports(retrieval_query)
    reference_chunks = chroma_service.retrieve_from_reference(retrieval_query)

    logger.info(
        "Retrieved %d report chunks + %d reference chunks (retrieval_query='%s')",
        len(report_chunks),
        len(reference_chunks),
        retrieval_query[:60],
    )

    # ── Step 3: Format context ────────────────────────────────────────────────
    report_context = _format_chunks(report_chunks)
    reference_context = _format_chunks(reference_chunks)

    # ── Step 4: Build LangChain message history ───────────────────────────────
    history_messages = _build_lc_messages(windowed_history)

    # ── Step 5: Generate answer — always attempt, never refuse ───────────────
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", _HUMAN_PROMPT),
    ])

    response = (prompt | llm).invoke({
        "question": question,
        "report_context": report_context,
        "reference_context": reference_context,
        "chat_history": history_messages,
    })

    # ── Step 6: Score confidence + build citations ────────────────────────────
    confidence = _score_confidence(report_chunks, reference_chunks)
    source_citations = _build_citations(report_chunks, reference_chunks)
    latency_ms = int((time.monotonic() - t_start) * 1000)

    logger.info(
        "Q&A complete — confidence=%s, citations=%d, latency=%dms",
        confidence, len(source_citations), latency_ms,
    )

    return QAResponse(
        question=question,
        rewritten_query=rewritten_query,
        report_chunks=report_chunks,
        reference_chunks=reference_chunks,
        answer=response.content.strip(),
        refused=False,
        source_citations=source_citations,
        confidence=confidence,
        latency_ms=latency_ms,
    )

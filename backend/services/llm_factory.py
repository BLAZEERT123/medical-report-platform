"""
LLM factory — returns the correct LangChain LLM/Embeddings object based on settings.
Compatible with langchain 0.3.x, langchain-google-genai 2.x, Python 3.13.
"""
from __future__ import annotations

import time
import logging
from functools import lru_cache

import requests as _requests
from langchain_core.embeddings import Embeddings

from backend.config import get_settings

logger = logging.getLogger(__name__)


# ── Custom REST-based Gemini Embeddings ───────────────────────────────────────
# LangChain's GoogleGenerativeAIEmbeddings uses gRPC which can be blocked.
# This class calls the plain HTTPS REST API directly instead.

class GeminiRestEmbeddings(Embeddings):
    """Direct REST-based Gemini embeddings — no gRPC, no timeouts."""

    def __init__(self, api_key: str, model: str = "text-embedding-004"):
        self.api_key = api_key
        self.model = model
        self.url = (
            f"https://generativelanguage.googleapis.com/v1"
            f"/models/{model}:embedContent?key={api_key}"
        )

    def _embed_one(self, text: str, retries: int = 4) -> list:
        """Embed one text chunk, with exponential backoff retry on 5xx errors."""
        for attempt in range(retries):
            try:
                resp = _requests.post(
                    self.url,
                    json={"content": {"parts": [{"text": text[:8000]}]}},
                    timeout=60,
                )
                if resp.ok:
                    return resp.json()["embedding"]["values"]

                # Only retry on server errors (5xx); fail fast on client errors (4xx)
                if resp.status_code < 500:
                    logger.error("Gemini embed API error %s: %s", resp.status_code, resp.text)
                    resp.raise_for_status()

                wait = 2 ** attempt
                logger.warning(
                    "Gemini embed attempt %d/%d got %s — retrying in %ds",
                    attempt + 1, retries, resp.status_code, wait,
                )
                time.sleep(wait)

            except _requests.exceptions.Timeout:
                wait = 2 ** attempt
                logger.warning("Gemini embed timeout (attempt %d/%d), retrying in %ds",
                               attempt + 1, retries, wait)
                time.sleep(wait)

        raise RuntimeError(f"Gemini embedding failed after {retries} retries.")

    def embed_documents(self, texts: list) -> list:
        result = []
        for i, text in enumerate(texts):
            result.append(self._embed_one(text))
            # Gentle rate-limit: pause between each request
            if i < len(texts) - 1:
                time.sleep(0.5)
        return result

    def embed_query(self, text: str) -> list:
        return self._embed_one(text)


# ── LLM ───────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_llm():
    """Return a cached LangChain chat model based on configured provider."""
    settings = get_settings()

    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
            max_output_tokens=8192,   # increased from 2048 — long reports need more tokens
            max_retries=1,
        )
    elif settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-haiku-20240307",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.2,
            max_tokens=4096,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.openai_api_key,
            temperature=0.2,
            max_tokens=4096,
        )


# ── Embeddings ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_embeddings():
    """Return the embedding function based on provider setting."""
    settings = get_settings()

    if settings.embedding_provider == "gemini":
        return GeminiRestEmbeddings(api_key=settings.gemini_api_key)

    elif settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model="text-embedding-ada-002",
            openai_api_key=settings.openai_api_key,
        )
    else:
        # Local fallback — no API key needed, runs on CPU
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

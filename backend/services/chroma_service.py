"""
Chroma Vector Store Service.
Manages two collections:
  - Store A ("report_chunks"): chunks from user-uploaded reports
  - Store B ("reference_corpus"): pre-indexed MedlinePlus/WHO reference articles
Provides add and retrieve operations for both stores.
"""
from __future__ import annotations
import logging
from typing import List
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.config import get_settings
from backend.models.report import ReportData, RetrievedChunk
from backend.services.llm_factory import get_embeddings
logger = logging.getLogger(__name__)
_client: chromadb.PersistentClient | None = None
def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client
def _get_collection(name: str):
    client = _get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 128) -> List[str]:
    """Split text into overlapping chunks by character count."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
import time

def _embed_with_retry(fn, *args, retries=3):
    """Call fn(*args) with exponential backoff retry on network errors."""
    for attempt in range(retries):
        try:
            return fn(*args)
        except Exception as exc:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning("Embed attempt %d/%d failed (%s), retrying in %ds", attempt+1, retries, exc, wait)
                time.sleep(wait)
            else:
                raise

def _embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of strings using the configured embedding model."""
    embedder = get_embeddings()
    return _embed_with_retry(embedder.embed_documents, texts)

def _embed_query(query: str) -> List[float]:
    embedder = get_embeddings()
    return _embed_with_retry(embedder.embed_query, query)

# ── Store A: Report Chunks ────────────────────────────────────────────────────
def index_report(report: ReportData, report_id: int, raw_text: str) -> int:
    """
    Chunk and index the OCR text + structured summary of a report into Store A.
    Returns number of chunks indexed.
    """
    settings = get_settings()
    collection = _get_collection(settings.report_collection)
    # Build rich text to index: both raw OCR text and structured test data
    structured_text = _report_to_text(report)
    full_text = f"{raw_text}\n\n---STRUCTURED SUMMARY---\n{structured_text}"
    chunks = _chunk_text(full_text)
    embeddings = _embed(chunks)
    ids = [f"report_{report_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "report_id": report_id,
            "patient": report.patient,
            "report_date": report.report_date,
            "report_type": report.report_type.value,
            "chunk_index": i,
            "source_name": f"Your {report.report_type.value} report ({report.report_date})",
        }
        for i in range(len(chunks))
    ]
    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    logger.info("Indexed %d chunks for report_id=%d in Store A", len(chunks), report_id)
    return len(chunks)
def _report_to_text(report: ReportData) -> str:
    """Convert structured ReportData to a searchable text block."""
    lines = [
        f"Patient: {report.patient}",
        f"Date: {report.report_date}",
        f"Type: {report.report_type.value}",
    ]
    for t in report.tests:
        lines.append(
            f"{t.name}: {t.value} {t.unit} "
            f"(ref: {t.reference_range}) [{t.status.value}]"
        )
    return "\n".join(lines)
def _keyword_retrieve(collection, query: str, k: int, source_type: str) -> List[RetrievedChunk]:
    """Keyword-based retrieval fallback — no embedding API needed."""
    logger.info("Using keyword retrieval fallback for query: %s", query[:60])
    # Extract meaningful words (skip common stop words)
    stop = {"what","is","are","the","my","i","a","an","do","does","how","why","when","should"}
    keywords = [w.lower() for w in query.split() if len(w) > 3 and w.lower() not in stop]
    if not keywords:
        keywords = query.split()[:3]

    matched = []
    try:
        all_docs = collection.get(include=["documents", "metadatas"])
        for doc, meta in zip(all_docs["documents"], all_docs["metadatas"]):
            doc_lower = doc.lower()
            hits = sum(1 for kw in keywords if kw in doc_lower)
            if hits > 0:
                matched.append((hits, doc, meta))
        matched.sort(key=lambda x: x[0], reverse=True)
    except Exception as exc:
        logger.warning("Keyword retrieval failed: %s", exc)
        return []

    chunks = []
    for hits, doc, meta in matched[:k]:
        score = round(min(hits / max(len(keywords), 1), 1.0), 4)
        if source_type == "report":
            chunks.append(RetrievedChunk(
                source_type="report",
                source_name=meta.get("source_name", "Your report"),
                snippet=doc[:400],
                score=score,
                metadata=meta,
            ))
        else:
            chunks.append(RetrievedChunk(
                source_type="reference",
                source_name=meta.get("source_name", meta.get("title", "Reference")),
                source_url=meta.get("source_url"),
                snippet=doc[:400],
                score=score,
                metadata=meta,
            ))
    return chunks


def retrieve_from_reports(query: str, top_k: int | None = None) -> List[RetrievedChunk]:
    """Retrieve top-k chunks from Store A (user's reports)."""
    settings = get_settings()
    k = top_k or settings.retrieval_top_k
    collection = _get_collection(settings.report_collection)
    if collection.count() == 0:
        return []
    try:
        query_embedding = _embed_query(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = round(1 - dist, 4)
            chunks.append(RetrievedChunk(
                source_type="report",
                source_name=meta.get("source_name", "Your report"),
                snippet=doc[:400],
                score=score,
                metadata=meta,
            ))
        return chunks
    except Exception as exc:
        logger.warning("Vector retrieval failed for reports (%s) — using keyword fallback", exc)
        return _keyword_retrieve(collection, query, k, "report")
# ── Store B: Reference Corpus ─────────────────────────────────────────────────
def index_reference_article(
    text: str,
    title: str,
    source_url: str = "",
    article_id: str = "",
) -> int:
    """Index a reference article (MedlinePlus, WHO, CDC) into Store B."""
    settings = get_settings()
    collection = _get_collection(settings.reference_collection)
    chunks = _chunk_text(text)
    embeddings = _embed(chunks)
    ids = [f"ref_{article_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "title": title,
            "source_url": source_url,
            "article_id": article_id,
            "chunk_index": i,
            "source_name": f"MedlinePlus: {title}" if "medlineplus" in source_url else title,
        }
        for i in range(len(chunks))
    ]
    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    logger.info("Indexed %d chunks for reference article '%s'", len(chunks), title)
    return len(chunks)
def retrieve_from_reference(query: str, top_k: int | None = None) -> List[RetrievedChunk]:
    """Retrieve top-k chunks from Store B (reference corpus)."""
    settings = get_settings()
    k = top_k or settings.retrieval_top_k
    collection = _get_collection(settings.reference_collection)
    if collection.count() == 0:
        return []
    try:
        query_embedding = _embed_query(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = round(1 - dist, 4)
            chunks.append(RetrievedChunk(
                source_type="reference",
                source_name=meta.get("source_name", meta.get("title", "Reference")),
                source_url=meta.get("source_url"),
                snippet=doc[:400],
                score=score,
                metadata=meta,
            ))
        return chunks
    except Exception as exc:
        logger.warning("Vector retrieval failed for reference (%s) — using keyword fallback", exc)
        return _keyword_retrieve(collection, query, k, "reference")
def get_store_stats() -> dict:
    """Return collection sizes for both stores."""
    settings = get_settings()
    report_col = _get_collection(settings.report_collection)
    ref_col = _get_collection(settings.reference_collection)
    return {
        "report_chunks": report_col.count(),
        "reference_corpus": ref_col.count(),
    }
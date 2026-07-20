# Medical Report Intelligence Platform

A production-quality medical report analysis platform that extracts structured clinical data from uploaded PDFs/images, explains findings in plain language, and answers follow-up questions with grounded, cited responses from both personal report data and trusted medical references.

## Features

| Feature | Description |
|---------|-------------|
| **OCR + Extraction** | Tesseract OCR → LangChain + PydanticOutputParser → strict JSON |
| **Rule-based Flagging** | Python logic (never LLM) flags NORMAL / BORDERLINE / ABNORMAL / CRITICAL |
| **Plain-language Summary** | LLM narrates pre-computed flagged findings |
| **Hybrid RAG Q&A** | Retrieves from personal report store (A) + MedlinePlus/WHO reference store (B) |
| **Retrieval Inspector** | Shows exact chunks retrieved from both stores *before* the LLM answer |
| **Citation Grounding** | Every answer cites its sources inline |
| **Refusal Guardrail** | LLM refuses to answer if no context is found in either store |

## Architecture

```
Upload (PDF/image)
      │
OCR (Tesseract) ──────── confidence check (warns if < 70%)
      │
LLM + PydanticOutputParser → strict ReportData JSON
      │
Rule-based flagging (Python) → NORMAL/BORDERLINE/ABNORMAL/CRITICAL
      │
LLM summary (narrates pre-computed flags only)
      │
   ┌─────────────────────────┐
   │                         │
SQLite (persist reports)   Chroma Store A (report chunks)
                             │
                           Chroma Store B (MedlinePlus/WHO — indexed once)
                             │
                    Hybrid retrieval + merge
                             │
                    LLM answer + inline citations
                             │
                    Streamlit UI (Retrieval Inspector)
```

## Guardrails

- **LLM never does arithmetic** — all flagging is pure Python comparisons
- **LLM never decides what is abnormal** — it only narrates pre-computed statuses
- **Refusal on empty context** — if neither store returns relevant chunks, the LLM refuses gracefully
- **Critical value urgency** — CRITICAL flags (e.g., Hb < 7, HbA1c > 10) trigger an urgent banner

## Project Structure

```
medical-report-platform/
├── backend/
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Pydantic settings
│   ├── models/report.py          # Strict Pydantic schemas
│   └── services/
│       ├── ocr_service.py        # Tesseract OCR + confidence
│       ├── extraction_service.py # LLM + PydanticOutputParser
│       ├── flagging_service.py   # Rule-based NORMAL/ABNORMAL logic
│       ├── summary_service.py    # LLM plain-language explanation
│       ├── store_service.py      # SQLite persistence
│       ├── chroma_service.py     # ChromaDB (Store A + Store B)
│       ├── qa_service.py         # Hybrid retrieval + answer
│       └── llm_factory.py        # LLM/embedding factory
├── frontend/app.py               # Streamlit UI
├── scripts/
│   ├── generate_sample_reports.py   # Create synthetic demo PDFs
│   └── index_reference_corpus.py    # Index MedlinePlus/WHO into Store B
├── tests/test_flagging.py        # Unit tests (rule-based logic)
└── requirements.txt
```

## Quick Start

### 1. Prerequisites

**Python 3.10+** required.

Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki):
- **Windows**: Download installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), install to `C:\Program Files\Tesseract-OCR`, add to PATH
- **Linux**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

Install [Poppler](https://poppler.freedesktop.org/) (for PDF support):
- **Windows**: Download from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases), add `bin/` to PATH
- **Linux**: `sudo apt install poppler-utils`
- **macOS**: `brew install poppler`

### 2. Install dependencies

```bash
cd medical-report-platform
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key:
#   OPENAI_API_KEY=sk-...
# Or use local embeddings (no key needed):
#   EMBEDDING_PROVIDER=local
```

### 4. Generate sample reports

```bash
python scripts/generate_sample_reports.py
# Creates 3 demo PDFs in backend/data/synthetic_reports/
```

### 5. Index the reference corpus (one-time)

```bash
python scripts/index_reference_corpus.py
# Scrapes MedlinePlus + indexes static WHO/CDC guidelines into Chroma Store B
# Requires internet access (~30 seconds)
```

### 6. Start the backend

```bash
# From project root
python -m backend.main
# OR
uvicorn backend.main:app --reload --port 8000
```

### 7. Start the frontend

```bash
streamlit run frontend/app.py
```

Open **http://localhost:8501** in your browser.

## Run Tests

```bash
# Unit tests for rule-based flagging (no API key needed)
pytest tests/test_flagging.py -v
```

## Configuration

Key settings in `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for LLM calls |
| `EMBEDDING_PROVIDER` | `local` | `local` (no cost) or `openai` |
| `LLM_MODEL` | `gpt-4o-mini` | Any OpenAI chat model |
| `OCR_CONFIDENCE_THRESHOLD` | `70` | Below this → show warning |
| `RETRIEVAL_TOP_K` | `3` | Chunks to retrieve per store |

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reports/upload` | Upload PDF/image → structured JSON + summary |
| `GET` | `/reports/` | List all stored reports |
| `GET` | `/reports/{id}` | Get specific report |
| `POST` | `/qa/ask` | Ask question → retrieval inspector + answer |
| `GET` | `/qa/store-stats` | ChromaDB collection sizes |
| `GET` | `/health` | Health check |

Interactive docs: **http://localhost:8000/docs**

## Resume Bullet

> Built an end-to-end medical report intelligence platform: extracts structured clinical data via OCR and Pydantic-enforced parsing, answers questions using a two-store hybrid RAG system (personal + trusted reference sources) with visible retrieval traces, computes flagging via rule-based Python logic (LLM never makes medical decisions), and generates grounded cited answers — using LangChain, FastAPI, ChromaDB, and Streamlit.

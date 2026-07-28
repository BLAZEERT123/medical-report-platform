# Medical Report Intelligence Platform

A production-quality medical report analysis platform that extracts structured clinical data from uploaded PDFs and images, explains findings in plain language, and answers follow-up questions with grounded, cited responses. It combines information from your personal report data with trusted medical references (like MedlinePlus and WHO).

It exists to help patients quickly understand their medical reports, translating complex medical jargon into easy-to-understand explanations while highlighting critical or abnormal values, without relying on LLMs to make medical decisions.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Tests](#tests)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Features

- **OCR + Extraction:** Uses Tesseract OCR and LangChain to reliably extract structured data (JSON) from medical reports.
- **Rule-based Flagging:** Uses pure Python logic (not LLMs) to accurately flag results as NORMAL, BORDERLINE, ABNORMAL, or CRITICAL.
- **Plain-language Summary:** An LLM narrates and explains pre-computed flagged findings in easy-to-understand language.
- **Hybrid RAG Q&A:** Retrieves context from a personal report store and a medical reference store (MedlinePlus/WHO) to answer questions.
- **Retrieval Inspector:** See the exact chunks retrieved from both vector stores before the LLM generates an answer.
- **Citation Grounding:** Every generated answer cites its sources inline.
- **Guardrails:** Refuses to answer if no context is found, ensuring it doesn't hallucinate medical advice.

## Architecture
The platform is split into a robust FastAPI Python backend and a modern React Vite frontend. 
Data is extracted using OCR, parsed via LangChain, and queried using ChromaDB for Retrieval-Augmented Generation (RAG).

## Installation

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**
- **Tesseract OCR:** 
  - Windows: [Download installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - Linux: `sudo apt install tesseract-ocr`
  - macOS: `brew install tesseract`
- **Poppler** (for PDF support):
  - Windows: [Download binaries](https://github.com/oschwartz10612/poppler-windows/releases) and add `bin/` to PATH.
  - Linux: `sudo apt install poppler-utils`
  - macOS: `brew install poppler`

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/BLAZEERT123/medical-report-platform.git
   cd medical-report-platform
   ```

2. **Setup the Backend:**
   ```bash
   # Create and activate virtual environment (optional but recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Setup the Frontend:**
   ```bash
   cd frontend-web
   npm install
   ```

## Configuration

1. Copy the example environment file in the root directory:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your configuration:
   ```env
   # Required for LLM usage
   OPENAI_API_KEY=sk-your-openai-api-key
   
   # Or use 'local' to avoid OpenAI costs for embeddings
   EMBEDDING_PROVIDER=local
   
   # Model selection (e.g. gpt-4o-mini)
   LLM_MODEL=gpt-4o-mini
   
   # OCR threshold below which a warning is displayed
   OCR_CONFIDENCE_THRESHOLD=70
   ```

## Usage

You can easily get both the backend and frontend running using the available tools, or manually via the terminal.

### 1. Initialize reference data (First time only)
Generate synthetic reports and index reference corpora so the RAG has data to search against.
```bash
# From project root
python scripts/generate_sample_reports.py
python scripts/index_reference_corpus.py
```

### 2. Start the Backend
```bash
# From project root
python -m backend.main
# The API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 3. Start the Frontend
In a new terminal window:
```bash
cd frontend-web
npm run dev
# The React UI will be available at http://localhost:5173
```

Open the frontend URL in your browser, upload a PDF/Image of a medical report, and explore the extracted data, summary, and Q&A features.

## Tests

To run the unit tests for the rule-based flagging logic:
```bash
# From project root
pytest tests/test_flagging.py -v
```

## Contributing
We welcome contributions! Feel free to open issues or submit pull requests for enhancements, bug fixes, or new features.

## License
This project is licensed under the MIT License.

## Acknowledgments
- Tesseract OCR for text extraction
- Streamlit (previous UI iteration) and React (current UI)
- LangChain for RAG workflows

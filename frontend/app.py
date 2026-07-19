"""
Medical Report Intelligence Platform — Streamlit Frontend
Features: Report Upload, Structured Extraction View, Q&A with Retrieval Inspector
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MedIntel — Medical Report Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").replace("localhost", "127.0.0.1")

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Dark glassmorphism background ── */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 40%, #0a1628 70%, #0e1320 100%);
    min-height: 100vh;
}

/* ── Remove default Streamlit padding ── */
.block-container { padding-top: 1.5rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(10, 20, 40, 0.85) !important;
    border-right: 1px solid rgba(64, 150, 255, 0.15);
    backdrop-filter: blur(20px);
}

/* ── Custom card ── */
.med-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(100,160,255,0.15);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    transition: border-color 0.2s ease;
}
.med-card:hover {
    border-color: rgba(100,160,255,0.35);
}

/* ── Test result badges ── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge-normal   { background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.badge-borderline { background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.badge-abnormal { background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
.badge-critical { background: rgba(220,38,38,0.3); color: #ff6b6b; border: 1px solid rgba(220,38,38,0.6);
                  animation: pulse 1.5s infinite; }
.badge-unknown  { background: rgba(156,163,175,0.2); color: #9ca3af; border: 1px solid rgba(156,163,175,0.3); }

@keyframes pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.4); }
    50% { box-shadow: 0 0 0 6px rgba(220,38,38,0); }
}

/* ── Urgency banner ── */
.urgency-banner {
    background: linear-gradient(135deg, rgba(220,38,38,0.3), rgba(185,28,28,0.2));
    border: 1.5px solid rgba(239,68,68,0.6);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
    animation: borderPulse 2s infinite;
}
@keyframes borderPulse {
    0%,100% { border-color: rgba(239,68,68,0.6); }
    50% { border-color: rgba(239,68,68,1.0); }
}

/* ── OCR warning ── */
.ocr-warning {
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.4);
    border-radius: 10px;
    padding: 0.75rem 1.25rem;
    margin-bottom: 1rem;
}

/* ── Retrieval inspector chunks ── */
.chunk-report {
    background: rgba(59,130,246,0.08);
    border-left: 3px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 13px;
}
.chunk-reference {
    background: rgba(16,185,129,0.08);
    border-left: 3px solid #10b981;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 13px;
}
.chunk-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.chunk-label-report { color: #60a5fa; }
.chunk-label-ref { color: #34d399; }
.score-pill {
    display: inline-block;
    font-size: 10px;
    padding: 1px 8px;
    border-radius: 20px;
    background: rgba(255,255,255,0.08);
    color: #94a3b8;
    margin-top: 4px;
}

/* ── Summary box ── */
.summary-box {
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 12px;
    padding: 1.25rem;
    line-height: 1.7;
    color: #e2e8f0;
    font-size: 14px;
}

/* ── Answer box ── */
.answer-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(100,160,255,0.2);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    line-height: 1.75;
    color: #e2e8f0;
    font-size: 14px;
}

/* ── Metric override ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(100,160,255,0.12);
    border-radius: 12px;
    padding: 0.75rem 1rem;
}

/* ── Tab styling ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #94a3b8;
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.25) !important;
    color: #a5b4fc !important;
}

/* ── Buttons ── */
.stButton>button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 25px rgba(99,102,241,0.4);
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.03);
    border: 2px dashed rgba(99,102,241,0.4);
    border-radius: 14px;
}

/* ── Headings ── */
h1, h2, h3 { font-family: 'Outfit', sans-serif; color: #e2e8f0; }
h1 { font-size: 2rem; }
h2 { font-size: 1.4rem; color: #94a3b8; font-weight: 600; }
/* ── Chat message overrides ── */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(100,160,255,0.1) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
    margin-bottom: 0.5rem !important;
}

/* ── Confidence badges ── */
.conf-high   { background: rgba(16,185,129,0.2); color: #34d399;
               border: 1px solid rgba(16,185,129,0.35); border-radius: 20px;
               padding: 2px 10px; font-size: 11px; font-weight: 700; }
.conf-medium { background: rgba(245,158,11,0.2); color: #fbbf24;
               border: 1px solid rgba(245,158,11,0.35); border-radius: 20px;
               padding: 2px 10px; font-size: 11px; font-weight: 700; }
.conf-low    { background: rgba(239,68,68,0.15); color: #f87171;
               border: 1px solid rgba(239,68,68,0.3); border-radius: 20px;
               padding: 2px 10px; font-size: 11px; font-weight: 700; }

/* ── Quick-start question buttons ── */
.stButton>button.quick-btn {
    background: rgba(99,102,241,0.12) !important;
    border: 1px solid rgba(99,102,241,0.3) !important;
    color: #a5b4fc !important;
    font-size: 12px !important;
    padding: 0.4rem 0.75rem !important;
    border-radius: 8px !important;
    transition: all 0.2s ease;
}
.stButton>button.quick-btn:hover {
    background: rgba(99,102,241,0.25) !important;
    transform: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def api_post(endpoint: str, **kwargs) -> Optional[Dict]:
    try:
        resp = requests.post(f"{BACKEND_URL}{endpoint}", **kwargs, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to backend. Make sure the FastAPI server is running on port 8000.")
        return None
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"❌ API Error: {detail}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None


def api_get(endpoint: str) -> Optional[Any]:
    try:
        resp = requests.get(f"{BACKEND_URL}{endpoint}", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def status_badge(status: str) -> str:
    cls_map = {
        "NORMAL": "badge-normal",
        "BORDERLINE": "badge-borderline",
        "ABNORMAL": "badge-abnormal",
        "CRITICAL": "badge-critical",
        "UNKNOWN": "badge-unknown",
    }
    icon_map = {
        "NORMAL": "✓",
        "BORDERLINE": "~",
        "ABNORMAL": "↑",
        "CRITICAL": "⚠",
        "UNKNOWN": "?",
    }
    cls = cls_map.get(status, "badge-unknown")
    icon = icon_map.get(status, "")
    return f'<span class="badge {cls}">{icon} {status}</span>'


def render_test_table(tests: list):
    """Render test results as a CSS-grid div layout (avoids Streamlit HTML table quirks)."""
    if not tests:
        st.markdown(
            '<div style="padding:1.5rem;text-align:center;color:#64748b;'
            'background:rgba(255,255,255,0.03);border-radius:12px;'
            'border:1px dashed rgba(100,160,255,0.2);">'
            '⚠️ No test results could be extracted from this report.<br>'
            '<span style="font-size:12px;">Try re-uploading, or ensure the backend is running.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Header ──
    header = (
        '<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1.5fr 1.5fr;'
        'background:rgba(99,102,241,0.15);border-bottom:1px solid rgba(99,102,241,0.3);">'
        '<div style="padding:12px;color:#a5b4fc;font-weight:600;font-size:12px;letter-spacing:0.5px;">TEST NAME</div>'
        '<div style="padding:12px;color:#a5b4fc;font-weight:600;font-size:12px;text-align:center;">VALUE</div>'
        '<div style="padding:12px;color:#a5b4fc;font-weight:600;font-size:12px;text-align:center;">UNIT</div>'
        '<div style="padding:12px;color:#a5b4fc;font-weight:600;font-size:12px;text-align:center;">REFERENCE RANGE</div>'
        '<div style="padding:12px;color:#a5b4fc;font-weight:600;font-size:12px;text-align:center;">STATUS</div>'
        '</div>'
    )

    # ── Rows ──
    rows = ""
    for t in tests:
        badge = status_badge(t["status"])
        if t["status"] == "CRITICAL":
            row_bg = "background:rgba(220,38,38,0.08);"
        elif t["status"] == "ABNORMAL":
            row_bg = "background:rgba(239,68,68,0.05);"
        else:
            row_bg = ""

        rows += (
            f'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1.5fr 1.5fr;'
            f'border-bottom:1px solid rgba(255,255,255,0.05);{row_bg}">'
            f'<div style="padding:10px 12px;color:#e2e8f0;font-weight:500;">{t["name"]}</div>'
            f'<div style="padding:10px 12px;color:#60a5fa;font-weight:600;text-align:center;">{t["value"]}</div>'
            f'<div style="padding:10px 12px;color:#94a3b8;text-align:center;">{t["unit"]}</div>'
            f'<div style="padding:10px 12px;color:#94a3b8;text-align:center;font-size:12px;">{t["reference_range"]}</div>'
            f'<div style="padding:10px 12px;text-align:center;">{badge}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="border-radius:12px;border:1px solid rgba(100,160,255,0.15);overflow:hidden;">'
        f'{header}{rows}'
        f'</div>',
        unsafe_allow_html=True,
    )



def render_retrieval_inspector(report_chunks: list, ref_chunks: list):
    """Render the Retrieval Inspector panel — Store A above Store B (vertical layout)."""
    st.markdown("### 🔍 Retrieval Inspector")
    st.caption("Showing the exact chunks retrieved from both stores before the LLM generated its answer.")

    # ── Store A: Your Reports ──
    st.markdown(
        '<p style="color:#60a5fa;font-weight:700;font-size:12px;letter-spacing:1px;'
        'text-transform:uppercase;margin-bottom:8px;">🗂 Store A — Your Reports</p>',
        unsafe_allow_html=True,
    )
    if report_chunks:
        for chunk in report_chunks:
            score_pct = int(chunk.get("score", 0) * 100)
            st.markdown(
                f"""<div class="chunk-report">
                <div class="chunk-label chunk-label-report">📋 {chunk['source_name']}</div>
                <div style="color:#cbd5e1;line-height:1.5;">{chunk['snippet'][:300]}...</div>
                <span class="score-pill">Similarity: {score_pct}%</span>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#64748b;font-style:italic;padding:1rem;'
            'background:rgba(255,255,255,0.02);border-radius:8px;'
            'border:1px dashed rgba(100,160,255,0.15);text-align:center;margin-bottom:0.5rem;">'
            'No relevant chunks from your reports</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ── Store B: Reference Sources ──
    st.markdown(
        '<p style="color:#34d399;font-weight:700;font-size:12px;letter-spacing:1px;'
        'text-transform:uppercase;margin-bottom:8px;">📚 Store B — Reference Sources</p>',
        unsafe_allow_html=True,
    )
    if ref_chunks:
        for chunk in ref_chunks:
            score_pct = int(chunk.get("score", 0) * 100)
            source_url = chunk.get("source_url", "")
            url_html = (
                f' <a href="{source_url}" target="_blank" style="color:#34d399;font-size:10px;">↗</a>'
                if source_url else ""
            )
            st.markdown(
                f"""<div class="chunk-reference">
                <div class="chunk-label chunk-label-ref">📖 {chunk['source_name']}{url_html}</div>
                <div style="color:#cbd5e1;line-height:1.5;">{chunk['snippet'][:300]}...</div>
                <span class="score-pill">Similarity: {score_pct}%</span>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#64748b;font-style:italic;padding:1rem;'
            'background:rgba(255,255,255,0.02);border-radius:8px;'
            'border:1px dashed rgba(16,185,129,0.15);text-align:center;">'
            'No relevant chunks from reference sources</div>',
            unsafe_allow_html=True,
        )


# ── Session state ─────────────────────────────────────────────────────────────
if "uploaded_report" not in st.session_state:
    st.session_state.uploaded_report = None
if "messages" not in st.session_state:
    st.session_state.messages = []          # {role, content, meta?}
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.now()



# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0;">
        <div style="font-size:2.5rem;">🏥</div>
        <div style="font-family:'Outfit',sans-serif;font-size:1.3rem;font-weight:700;
             color:#e2e8f0;margin-top:4px;">MedIntel</div>
        <div style="color:#64748b;font-size:11px;margin-top:2px;">
            Medical Report Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Backend health
    health = api_get("/health")
    if health:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;'
            'background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);'
            'border-radius:8px;">'
            '<span style="color:#34d399;font-size:18px;">●</span>'
            '<span style="color:#94a3b8;font-size:12px;">Backend connected</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;'
            'background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);'
            'border-radius:8px;">'
            '<span style="color:#f87171;font-size:18px;">●</span>'
            '<span style="color:#94a3b8;font-size:12px;">Backend offline</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Store stats
    stats = api_get("/qa/store-stats")
    if stats:
        st.markdown('<p style="color:#94a3b8;font-size:11px;font-weight:600;letter-spacing:0.5px;">VECTOR STORE STATUS</p>', unsafe_allow_html=True)
        st.metric("📋 Report Chunks", stats.get("report_chunks", 0))
        st.metric("📚 Reference Chunks", stats.get("reference_corpus", 0))

    st.divider()

    # Past reports
    reports = api_get("/reports/") or []
    if reports:
        st.markdown('<p style="color:#94a3b8;font-size:11px;font-weight:600;letter-spacing:0.5px;">UPLOADED REPORTS</p>', unsafe_allow_html=True)
        for r in reports[:5]:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f'<div style="font-size:12px;color:#cbd5e1;padding:4px 0;">'
                    f'📄 {r["patient"]}<br>'
                    f'<span style="color:#64748b;font-size:10px;">{r["report_date"]} · {r["report_type"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ── Main content ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.5rem;">
    <h1 style="margin:0;background:linear-gradient(135deg,#60a5fa,#a78bfa,#34d399);
       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
       font-family:'Outfit',sans-serif;font-size:2.2rem;">
       Medical Report Intelligence
    </h1>
    <p style="color:#64748b;margin-top:4px;font-size:14px;">
       Upload lab reports → Extract structured data → Ask questions with grounded citations
    </p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📤  Upload & Analyze", "💬  Q&A with Sources", "📊  Trends"])

# ════════════════════════════════════════════════════════════════════════
# TAB 1: Upload & Analyze
# ════════════════════════════════════════════════════════════════════════
with tab1:
    # ── Upload row (compact, full-width) ──────────────────────────────────
    st.markdown("### 📤 Upload Report")
    up_col, btn_col = st.columns([3, 1], gap="small")
    with up_col:
        uploaded_file = st.file_uploader(
            "Upload a PDF or image of your lab report",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
            help="Supports: PDF, PNG, JPG, JPEG, TIFF, BMP",
            label_visibility="collapsed",
        )
    with btn_col:
        st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
        analyze_btn = st.button(
            "🔬 Analyze Report",
            disabled=uploaded_file is None,
            use_container_width=True,
        )

    if uploaded_file:
        st.markdown(
            f'<div style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.3);'
            f'border-radius:8px;padding:6px 12px;font-size:12px;color:#a5b4fc;margin-bottom:0.5rem;">'
            f'📄 {uploaded_file.name} ({uploaded_file.size // 1024} KB)</div>',
            unsafe_allow_html=True,
        )

    if analyze_btn and uploaded_file:
        with st.spinner("🔍 Running OCR and extracting data..."):
            data = api_post(
                "/reports/upload",
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
            )
        if data:
            st.session_state.uploaded_report = data
            st.success(f"✅ Report analyzed! ID: #{data['report_id']}")

    if not uploaded_file:
        st.markdown("""
        <div style="padding:1rem;background:rgba(255,255,255,0.03);
             border-radius:12px;border:1px solid rgba(255,255,255,0.07);margin-bottom:1rem;">
            <p style="color:#64748b;font-size:13px;margin:0 0 4px;">
                <strong style="color:#94a3b8;">Supported formats:</strong> PDF · PNG · JPG · TIFF · BMP
            </p>
            <p style="color:#64748b;font-size:12px;margin:0;">
                Sample PDFs: run <code style="background:rgba(255,255,255,0.08);padding:1px 6px;border-radius:4px;">
                python scripts/generate_sample_reports.py</code>
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Results (full-width below upload) ─────────────────────────────────
    report = st.session_state.uploaded_report

    if report:
        structured = report.get("structured") or report.get("structured_report")
        ocr = report.get("ocr", {})

        if not structured:
            st.error("⚠️ Report data is incomplete — see raw response below.")
            st.json(report)
        else:
            # ── OCR Warning ──
            if report.get("ocr_warning"):
                st.markdown(
                    f'<div class="ocr-warning">⚠️ <strong>Low OCR Confidence: {ocr.get("confidence",0):.1f}%</strong>'
                    f' — The scan quality may be poor. Verify values manually.</div>',
                    unsafe_allow_html=True,
                )

            # ── Urgency Banner ──
            if report.get("urgency"):
                st.markdown(
                    '<div class="urgency-banner">'
                    '🚨 <strong style="color:#fca5a5;">URGENT:</strong>'
                    '<span style="color:#fca5a5;"> One or more CRITICAL values detected. '
                    'Please contact your doctor immediately.</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            # ── Patient Info ──
            st.markdown("### Patient Information")
            c1, c2, c3 = st.columns(3)
            c1.metric("👤 Patient", structured.get("patient", "N/A"))
            c2.metric("📅 Date", structured.get("report_date", "N/A"))
            c3.metric("🧪 Type", structured.get("report_type", "N/A"))
            if structured.get("lab_name"):
                st.caption(f"🏥 Lab: {structured['lab_name']} | 👨‍⚕️ Dr. {structured.get('doctor','N/A')}")

            # ── Test Results Table ──
            st.markdown("### Test Results")
            render_test_table(structured.get("tests", []))

            # ── Status Summary counts ──
            from collections import Counter
            status_counts = Counter(t["status"] for t in structured.get("tests", []))
            s_cols = st.columns(4)
            for idx, (stat, clr) in enumerate([
                ("CRITICAL", "#f87171"), ("ABNORMAL", "#fb923c"),
                ("BORDERLINE", "#fbbf24"), ("NORMAL", "#34d399"),
            ]):
                s_cols[idx].markdown(
                    f'<div style="text-align:center;padding:8px;">'
                    f'<div style="font-size:1.5rem;font-weight:700;color:{clr};">{status_counts.get(stat, 0)}</div>'
                    f'<div style="font-size:10px;color:#64748b;letter-spacing:0.5px;">{stat}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # ── Plain-language Summary ──
            st.markdown("### 💬 Plain-Language Explanation")
            summary_text = report.get("summary") or report.get("explanation") or ""
            import re as _re
            summary_clean = _re.sub(r"<[^>]+>", "", summary_text).strip()
            summary_html = summary_clean.replace("\n\n", "</p><p>").replace("\n", "<br>")
            st.markdown(
                f'<div class="summary-box"><p>{summary_html}</p></div>',
                unsafe_allow_html=True,
            )

            # ── OCR Details (collapsed) ──
            with st.expander(
                f"🔤 OCR Details — Confidence: {ocr.get('confidence',0):.1f}%"
                f"  ({ocr.get('page_count',1)} page(s))"
            ):
                st.code(ocr.get("text", "")[:3000], language=None)




# ════════════════════════════════════════════════════════════════════════
# TAB 2: Q&A Chatbot with Retrieval Inspector
# Inspired by Ratnesh-181998/Medical-RAG-Chatbot's Streamlit UI patterns:
# - native st.chat_message() for proper chat bubbles
# - immediate response generation (no double-rerun flash)
# - inline confidence + latency display
# ════════════════════════════════════════════════════════════════════════
with tab2:

    # ── Header row ────────────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([7, 3])
    with hdr_l:
        st.markdown("""
        <div style="margin-bottom:0.5rem;">
            <h2 style="margin:0;font-family:'Outfit',sans-serif;font-size:1.6rem;
               background:linear-gradient(135deg,#60a5fa,#a78bfa);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
               💬 Medical Q&A
            </h2>
            <p style="color:#64748b;font-size:12px;margin:2px 0 0 0;">
               RAG-powered answers grounded in your reports + medical reference sources
            </p>
        </div>
        """, unsafe_allow_html=True)
    with hdr_r:
        stat_a, stat_b = st.columns(2)
        stat_a.metric("💬 Asked", st.session_state.total_questions)
        session_mins = (datetime.now() - st.session_state.session_start_time).seconds // 60
        stat_b.metric("⏱️ Session", f"{session_mins}m")

    st.markdown("---")

    # ── Quick-start suggestion chips ──────────────────────────────────
    st.markdown(
        '<p style="color:#94a3b8;font-size:11px;font-weight:700;'
        'letter-spacing:0.8px;text-transform:uppercase;margin-bottom:8px;">'
        '⚡ Quick Questions</p>',
        unsafe_allow_html=True,
    )
    suggested_qs = [
        "What does low hemoglobin mean?",
        "Why is my HbA1c high?",
        "Is my cholesterol dangerous?",
        "What causes low platelets?",
        "How can I improve my kidney function?",
        "Symptoms of iron deficiency?",
        "What is a normal blood pressure?",
        "What causes high glucose levels?",
    ]
    q_cols = st.columns(4)
    for i, q in enumerate(suggested_qs):
        with q_cols[i % 4]:
            if st.button(q, key=f"sq_{i}", use_container_width=True):
                st.session_state["_pending_q"] = q

    # Flush pending quick-start query into messages immediately
    if "_pending_q" in st.session_state:
        pending = st.session_state.pop("_pending_q")
        st.session_state.messages.append({"role": "user", "content": pending})
        st.session_state.total_questions += 1

    st.markdown("---")

    # ── Action bar (export + clear) ───────────────────────────────────
    act_l, act_m, act_r = st.columns([5, 1, 1])
    with act_l:
        st.markdown(
            '<p style="color:#64748b;font-size:12px;margin:0.4rem 0;">'
            'Ask about any medical term, lab value, or medication — '
            'answers are grounded in your uploaded reports.</p>',
            unsafe_allow_html=True,
        )
    with act_m:
        has_msgs = len(st.session_state.messages) > 0
        if st.button("🗑 Clear", use_container_width=True, disabled=not has_msgs, key="clear_chat"):
            st.session_state.messages = []
            st.session_state.total_questions = 0
            st.rerun()
    with act_r:
        if has_msgs if 'has_msgs' in dir() else len(st.session_state.messages) > 0:
            export_lines = ["MEDICAL Q&A — CONVERSATION EXPORT"]
            export_lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            export_lines.append("=" * 50)
            for m in st.session_state.messages:
                role_label = "YOU" if m["role"] == "user" else "AI"
                export_lines.append(f"\n[{role_label}]\n{m['content']}")
            st.download_button(
                "💾 Export",
                data="\n".join(export_lines),
                file_name=f"medical_qa_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="export_btn",
            )

    # ── Chat message history (native Streamlit chat) ──────────────────
    # Render ALL existing messages first
    for msg in st.session_state.messages:
        with st.chat_message(
            msg["role"],
            avatar="👤" if msg["role"] == "user" else "🩺",
        ):
            # User bubble — plain text
            if msg["role"] == "user":
                st.markdown(msg["content"])

            # Assistant bubble — answer + metadata badges
            else:
                st.markdown(msg["content"])

                # Inline meta row: confidence + latency + rewritten query
                meta = msg.get("meta", {})
                conf = meta.get("confidence", "")
                latency = meta.get("latency_ms", None)
                rewritten = meta.get("rewritten_query", None)

                meta_parts = []
                if conf == "High":
                    meta_parts.append('<span class="conf-high">● High Confidence</span>')
                elif conf == "Medium":
                    meta_parts.append('<span class="conf-medium">● Medium Confidence</span>')
                elif conf == "Low":
                    meta_parts.append('<span class="conf-low">● Low Confidence</span>')
                if latency:
                    meta_parts.append(
                        f'<span style="color:#64748b;font-size:11px;">⏱ {latency}ms</span>'
                    )
                if rewritten:
                    meta_parts.append(
                        f'<span style="color:#7c3aed;font-size:11px;" '
                        f'title="Query was rewritten for better retrieval">'
                        f'🔄 Query rewritten</span>'
                    )

                if meta_parts:
                    st.markdown(
                        '<div style="margin-top:6px;display:flex;gap:8px;'
                        'align-items:center;flex-wrap:wrap;">'
                        + " ".join(meta_parts)
                        + "</div>",
                        unsafe_allow_html=True,
                    )

                # Retrieval Inspector inside expander
                report_chunks = msg.get("report_chunks", [])
                ref_chunks    = msg.get("reference_chunks", [])
                total_chunks  = len(report_chunks) + len(ref_chunks)
                if total_chunks > 0:
                    with st.expander(
                        f"🔍 Retrieval Inspector — {total_chunks} chunk(s) used",
                        expanded=False,
                    ):
                        render_retrieval_inspector(report_chunks, ref_chunks)

    # ── Chat input box ────────────────────────────────────────────────
    user_input = st.chat_input(
        "Ask a medical question — e.g. 'What does my high creatinine mean?'"
    )

    # ── Process input → generate response immediately (no double rerun) ──
    if user_input:
        # 1. Show user message right away
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.total_questions += 1

        # 2. Generate assistant response
        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner("🧠 Analyzing with RAG pipeline..."):
                api_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]  # exclude current user msg
                ]
                response = api_post("/qa/ask", json={
                    "question": user_input,
                    "chat_history": api_history,
                })

            if response:
                answer = response.get("answer", "No answer provided.")
                confidence = response.get("confidence", "")
                latency_ms = response.get("latency_ms", None)
                rewritten_q = response.get("rewritten_query", None)
                report_chunks = response.get("report_chunks", [])
                ref_chunks    = response.get("reference_chunks", [])

                st.markdown(answer)

                # Meta row
                meta_parts = []
                if confidence == "High":
                    meta_parts.append('<span class="conf-high">● High Confidence</span>')
                elif confidence == "Medium":
                    meta_parts.append('<span class="conf-medium">● Medium Confidence</span>')
                elif confidence:
                    meta_parts.append('<span class="conf-low">● Low Confidence</span>')
                if latency_ms:
                    meta_parts.append(
                        f'<span style="color:#64748b;font-size:11px;">⏱ {latency_ms}ms</span>'
                    )
                if rewritten_q:
                    meta_parts.append(
                        f'<span style="color:#7c3aed;font-size:11px;" '
                        f'title="Rewritten to: {rewritten_q}">🔄 Query rewritten</span>'
                    )
                if meta_parts:
                    st.markdown(
                        '<div style="margin-top:6px;display:flex;gap:8px;'
                        'align-items:center;flex-wrap:wrap;">'
                        + " ".join(meta_parts)
                        + "</div>",
                        unsafe_allow_html=True,
                    )

                # Retrieval Inspector
                total_chunks = len(report_chunks) + len(ref_chunks)
                if total_chunks > 0:
                    with st.expander(
                        f"🔍 Retrieval Inspector — {total_chunks} chunk(s) used",
                        expanded=False,
                    ):
                        render_retrieval_inspector(report_chunks, ref_chunks)

                # Save to session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "report_chunks": report_chunks,
                    "reference_chunks": ref_chunks,
                    "meta": {
                        "confidence": confidence,
                        "latency_ms": latency_ms,
                        "rewritten_query": rewritten_q,
                    },
                })
            else:
                err_msg = (
                    "⚠️ The AI couldn't generate a response right now. "
                    "Please check the backend is running and try again."
                )
                st.warning(err_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": err_msg,
                    "meta": {},
                })


# ════════════════════════════════════════════════════════════════════════
# TAB 3: Trends — Historical report overview
# ════════════════════════════════════════════════════════════════════════
with tab3:
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd

    st.markdown("### 📊 Report Trends")
    st.markdown(
        '<p style="color:#64748b;font-size:13px;margin-bottom:1rem;">'
        'Overview of all uploaded reports and their test result distributions.</p>',
        unsafe_allow_html=True,
    )

    all_reports = api_get("/reports/") or []

    if not all_reports:
        st.markdown("""
        <div style="height:350px;display:flex;flex-direction:column;align-items:center;
             justify-content:center;opacity:0.4;">
            <div style="font-size:4rem;margin-bottom:1rem;">📊</div>
            <div style="color:#64748b;font-size:14px;">Upload reports to see trends here</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── Summary metrics ──
        m1, m2, m3 = st.columns(3)
        m1.metric("📄 Total Reports", len(all_reports))
        unique_patients = len({r["patient"] for r in all_reports})
        m2.metric("👤 Unique Patients", unique_patients)
        report_types = list({r["report_type"] for r in all_reports})
        m3.metric("🧪 Report Types", len(report_types))

        st.divider()

        # ── Report type distribution ──
        type_counts = {}
        for r in all_reports:
            rtype = r.get("report_type", "OTHER")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

        col_pie, col_timeline = st.columns(2)

        with col_pie:
            st.markdown("**Report Type Distribution**")
            fig_pie = go.Figure(go.Pie(
                labels=list(type_counts.keys()),
                values=list(type_counts.values()),
                hole=0.5,
                marker=dict(
                    colors=["#4f46e5", "#7c3aed", "#10b981", "#f59e0b",
                            "#ef4444", "#60a5fa", "#34d399", "#a78bfa"],
                ),
            ))
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", size=12),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                margin=dict(t=20, b=20, l=0, r=0),
                height=280,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_timeline:
            st.markdown("**Upload Timeline**")
            df_reports = pd.DataFrame(all_reports)
            df_reports["uploaded_at"] = pd.to_datetime(
                df_reports["uploaded_at"], errors="coerce"
            ).dt.date
            timeline_counts = df_reports.groupby("uploaded_at").size().reset_index(name="count")
            fig_line = px.line(
                timeline_counts,
                x="uploaded_at",
                y="count",
                markers=True,
                color_discrete_sequence=["#60a5fa"],
            )
            fig_line.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(10,20,40,0.4)",
                font=dict(color="#94a3b8", size=12),
                xaxis=dict(gridcolor="rgba(100,160,255,0.1)", title="Date"),
                yaxis=dict(gridcolor="rgba(100,160,255,0.1)", title="Reports"),
                margin=dict(t=20, b=20, l=0, r=0),
                height=280,
            )
            st.plotly_chart(fig_line, use_container_width=True)

        # ── Reports table ──
        st.markdown("**All Uploaded Reports**")
        rows_html = ""
        for r in all_reports:
            rows_html += f"""
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                <td style="padding:10px 12px;color:#60a5fa;font-weight:600;">#{r['id']}</td>
                <td style="padding:10px 12px;color:#e2e8f0;">{r['patient']}</td>
                <td style="padding:10px 12px;color:#94a3b8;">{r['report_date']}</td>
                <td style="padding:10px 12px;color:#a5b4fc;">{r['report_type']}</td>
                <td style="padding:10px 12px;color:#64748b;font-size:12px;">{r.get('lab_name','—')}</td>
                <td style="padding:10px 12px;color:#64748b;font-size:11px;">{r.get('uploaded_at','—')[:19]}</td>
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto;border-radius:12px;border:1px solid rgba(100,160,255,0.15);margin-top:0.5rem;">
        <table style="width:100%;border-collapse:collapse;background:rgba(255,255,255,0.02);">
            <thead>
                <tr style="background:rgba(99,102,241,0.15);border-bottom:1px solid rgba(99,102,241,0.3);">
                    <th style="padding:12px;color:#a5b4fc;text-align:left;font-size:12px;">ID</th>
                    <th style="padding:12px;color:#a5b4fc;text-align:left;font-size:12px;">PATIENT</th>
                    <th style="padding:12px;color:#a5b4fc;text-align:left;font-size:12px;">DATE</th>
                    <th style="padding:12px;color:#a5b4fc;text-align:left;font-size:12px;">TYPE</th>
                    <th style="padding:12px;color:#a5b4fc;text-align:left;font-size:12px;">LAB</th>
                    <th style="padding:12px;color:#a5b4fc;text-align:left;font-size:12px;">UPLOADED</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

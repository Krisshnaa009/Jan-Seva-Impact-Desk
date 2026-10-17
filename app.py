"""
JanSeva Impact Desk — NGO Report & Receipt Engine
Main Streamlit Application

Run with: streamlit run app.py
"""
from __future__ import annotations

import sys
import os

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

# Ensure project root is in the Python path when running via streamlit
sys.path.insert(0, os.path.dirname(__file__))

from decimal import Decimal
from io import BytesIO
from typing import List, Optional

import streamlit as st

from models.expense import ExpenseCategory, ExpenseRecord, ExpenseStatus
from services.receipt_extractor import extract_receipt, get_demo_records
from services.report_service import calculate_summary, get_approved_records
from services.validation_service import validate_all, validate_record
from services.pdf_service import generate_pdf_report, generate_narrative_summary
from utils.config import get_config

# ─────────────────────────────────────────────
# Page configuration (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="JanSeva Impact Desk",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS — modern, clean theme
# ─────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root variables ── */
:root {
    --primary: #1a6b3c;
    --primary-light: #2d9a5e;
    --primary-bg: #f0faf4;
    --accent: #16a34a;
    --warning: #d97706;
    --error: #dc2626;
    --surface: #ffffff;
    --surface-2: #f9fafb;
    --border: #e5e7eb;
    --text-primary: #111827;
    --text-secondary: #6b7280;
    --radius: 12px;
    --shadow: 0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.04);
}

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── Hide streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── App background & Main text contrast ── */
.stApp {
    background: #f8fdf9 !important;
    color: #111827 !important;
}

/* Ensure all text in main container is crisp and visible regardless of system dark/light mode */
.stApp section.main,
.stApp [data-testid="stMain"],
.stApp [data-testid="stMain"] p,
.stApp [data-testid="stMain"] span,
.stApp [data-testid="stMain"] label,
.stApp [data-testid="stMain"] div {
    color: #1f2937;
}

.stApp [data-testid="stMain"] h1,
.stApp [data-testid="stMain"] h2,
.stApp [data-testid="stMain"] h3,
.stApp [data-testid="stMain"] h4 {
    color: #0f4c2a !important;
    font-weight: 700 !important;
}

/* ── Expanders ── */
div[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 10px !important;
    margin-bottom: 0.75rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}
div[data-testid="stExpander"] details {
    background: #ffffff !important;
}
div[data-testid="stExpander"] summary {
    background: #f9fafb !important;
    color: #111827 !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}
div[data-testid="stExpander"] summary:hover {
    background: #f0fdf4 !important;
    color: #1a6b3c !important;
}
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] summary p {
    color: #111827 !important;
    font-weight: 600 !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f4c2a 0%, #1a6b3c 60%, #22c55e22 100%);
    border-right: none;
}
section[data-testid="stSidebar"] * { color: #d1fae5 !important; }
section[data-testid="stSidebar"] .stRadio label { color: #a7f3d0 !important; font-size: 0.9rem; }
section[data-testid="stSidebar"] h1, 
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #ffffff !important; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    box-shadow: var(--shadow);
    transition: transform .15s ease, box-shadow .15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(26,107,60,.12);
}
[data-testid="stMetricLabel"] { font-weight: 600; color: var(--text-secondary) !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: .04em; }
[data-testid="stMetricValue"] { color: var(--primary) !important; font-weight: 700; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1a6b3c, #2d9a5e);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    letter-spacing: .02em;
    transition: all .2s ease;
    box-shadow: 0 2px 8px rgba(26,107,60,.25);
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(26,107,60,.35);
    background: linear-gradient(135deg, #155c33, #24855a);
}

/* ── Section cards ── */
.section-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow);
}

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: .04em;
}
.badge-approved  { background: #dcfce7; color: #15803d; }
.badge-pending   { background: #fef9c3; color: #854d0e; }
.badge-needs     { background: #fee2e2; color: #b91c1c; }
.badge-rejected  { background: #f3f4f6; color: #6b7280; }

/* ── Alert boxes ── */
.alert-warning {
    background: #fffbeb;
    border-left: 4px solid var(--warning);
    border-radius: 0 8px 8px 0;
    padding: .75rem 1rem;
    margin: .5rem 0;
    font-size: 0.85rem;
    color: #78350f;
}
.alert-error {
    background: #fef2f2;
    border-left: 4px solid var(--error);
    border-radius: 0 8px 8px 0;
    padding: .75rem 1rem;
    margin: .5rem 0;
    font-size: 0.85rem;
    color: #7f1d1d;
}
.alert-success {
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    border-radius: 0 8px 8px 0;
    padding: .75rem 1rem;
    margin: .5rem 0;
    font-size: 0.85rem;
    color: #14532d;
}
.alert-info {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: .75rem 1rem;
    margin: .5rem 0;
    font-size: 0.85rem;
    color: #1e3a5f;
}

/* ── Divider ── */
.divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

/* ── Tables ── */
.stDataFrame { border-radius: var(--radius); overflow: hidden; }

/* ── Mode badge ── */
.mode-ai   { background: #064e3b; color: #a7f3d0 !important; border: 1px solid #10b981; padding: 4px 12px; border-radius: 99px; font-size: .8rem; font-weight: 700; display: inline-block; }
.mode-mock { background: #78350f; color: #fde68a !important; border: 1px solid #f59e0b; padding: 4px 12px; border-radius: 99px; font-size: .8rem; font-weight: 700; display: inline-block; }
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────

def _init_session():
    if "records" not in st.session_state:
        st.session_state.records: List[ExpenseRecord] = []
    # Always refresh config so edits to .env take immediate effect
    st.session_state.config = get_config()
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"
    if "processed_files" not in st.session_state:
        st.session_state.processed_files: set = set()


_init_session()
cfg = st.session_state.config


# ─────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🌿 JanSeva Impact Desk")
    st.markdown(
        "<small style='color:#a7f3d0'>NGO Report & Receipt Engine</small>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "📤 Upload Receipts", "🔍 Review & Approve", "📄 Generate Report"],
        key="nav_radio",
    )
    st.session_state.page = page

    st.markdown("---")

    # AI / Mock mode indicator
    if cfg.gemini_api_key:
        st.markdown(
            '<span class="mode-ai">🤖 AI Mode Active</span>', unsafe_allow_html=True
        )
        st.markdown(
            f"<small>Model: {cfg.gemini_model}</small>", unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span class="mode-mock">🎭 Demo / Mock Mode</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "<small>Add GEMINI_API_KEY to enable AI extraction</small>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    record_count = len(st.session_state.records)
    st.markdown(
        f"<small>📋 {record_count} record{'s' if record_count != 1 else ''} in session</small>",
        unsafe_allow_html=True,
    )

    if record_count > 0 and st.button("🗑️ Clear All Records", use_container_width=True):
        st.session_state.records = []
        st.session_state.processed_files = set()
        st.rerun()


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

def _get_record_by_id(record_id: str) -> Optional[ExpenseRecord]:
    for r in st.session_state.records:
        if r.id == record_id:
            return r
    return None


def _update_record(updated: ExpenseRecord):
    for i, r in enumerate(st.session_state.records):
        if r.id == updated.id:
            st.session_state.records[i] = updated
            return


def _status_badge(status: ExpenseStatus) -> str:
    cls = {
        ExpenseStatus.APPROVED: "badge-approved",
        ExpenseStatus.PENDING: "badge-pending",
        ExpenseStatus.NEEDS_CORRECTION: "badge-needs",
        ExpenseStatus.REJECTED: "badge-rejected",
    }.get(status, "badge-pending")
    return f'<span class="badge {cls}">{status.value}</span>'


def _mode_badge(mode: str) -> str:
    if "ai" in mode.lower() and "fallback" not in mode.lower():
        return f'<span class="mode-ai">🤖 AI</span>'
    return f'<span class="mode-mock">🎭 Mock</span>'


# ─────────────────────────────────────────────
# PAGE: Dashboard
# ─────────────────────────────────────────────

def page_dashboard():
    st.markdown(
        "# 🌿 JanSeva Impact Desk\n"
        "*Turn receipts and field evidence into organized, review-ready NGO reports.*"
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    records = st.session_state.records

    if not records:
        st.markdown(
            '<div class="alert-info">👋 <strong>Welcome!</strong> No receipts loaded yet. '
            "Head to <b>Upload Receipts</b> to get started, or load the demo dataset below.</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(
                """
### What is JanSeva Impact Desk?

JanSeva Impact Desk is an AI-powered expense management tool built for small NGOs and 
community organisations. It helps you:

- 📤 **Upload receipt images** (PNG, JPG, JPEG)
- 🤖 **Extract data automatically** using AI (or use demo mode without any API key)
- ✅ **Review and validate** expenses with automatic error detection
- 📊 **Track spending** across projects and categories
- 📄 **Generate professional PDF reports** ready for donor and audit review

### Workflow
`Upload Receipts` → `Review & Approve` → `Generate Report`
"""
            )
        with col2:
            st.markdown("### Quick Start")
            if st.button("🎭 Load Demo Dataset", use_container_width=True):
                demo_records = get_demo_records()
                validate_all(demo_records)
                st.session_state.records = demo_records
                st.success(f"Loaded {len(demo_records)} demo receipts!")
                st.rerun()
        return

    summary = calculate_summary(records)

    # Metric cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Total Receipts", summary.total_records)
    c2.metric(
        "⏳ Pending Review",
        summary.pending_count + summary.needs_correction_count,
    )
    c3.metric("✅ Approved Expenses", summary.approved_count)
    c4.metric("💰 Total Approved", summary.total_approved_display)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Recent records
    st.markdown("### 📋 Recent Records")
    cols = st.columns([2, 2, 2, 2, 2])
    cols[0].markdown("**Date**")
    cols[1].markdown("**Vendor**")
    cols[2].markdown("**Amount**")
    cols[3].markdown("**Category**")
    cols[4].markdown("**Status**")
    st.markdown("<hr style='margin:4px 0; border-color:#e5e7eb'>", unsafe_allow_html=True)

    for rec in records[-10:][::-1]:
        cols = st.columns([2, 2, 2, 2, 2])
        cols[0].write(rec.date_display)
        cols[1].write(rec.vendor or "—")
        cols[2].write(rec.amount_display)
        cols[3].write(rec.category.value)
        cols[4].markdown(_status_badge(rec.status), unsafe_allow_html=True)

    if len(records) > 10:
        st.caption(f"Showing 10 of {len(records)} records. Go to Review & Approve to see all.")

    # Issue summary
    issues_records = [r for r in records if r.validation_issues]
    if issues_records:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(f"### ⚠️ {len(issues_records)} Record(s) Need Attention")
        for rec in issues_records[:5]:
            for issue in rec.validation_issues[:2]:
                icon = "🔴" if issue.severity == "error" else "🟡"
                st.markdown(
                    f'<div class="alert-{"error" if issue.severity == "error" else "warning"}">'
                    f'{icon} <b>#{rec.id[:8]}</b> ({rec.vendor or "Unknown Vendor"}): '
                    f"{issue.message}</div>",
                    unsafe_allow_html=True,
                )
        if len(issues_records) > 5:
            st.caption(f"… and {len(issues_records) - 5} more. Review all in the Review & Approve tab.")


# ─────────────────────────────────────────────
# PAGE: Upload Receipts
# ─────────────────────────────────────────────

def page_upload():
    st.markdown("## 📤 Upload Receipts")
    st.markdown(
        "Upload receipt images to extract expense data. "
        "Supported formats: PNG, JPG, JPEG (max 10 MB each)."
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Demo dataset callout
    st.markdown(
        '<div class="alert-info">💡 <strong>Hackathon Demo:</strong> No real receipts? '
        'Click <b>Load Demo Dataset</b> to instantly populate the app with 8 realistic '
        'fictional receipts (including intentional errors) to explore all features.</div>',
        unsafe_allow_html=True,
    )

    col_demo, _ = st.columns([1, 3])
    with col_demo:
        if st.button("🎭 Load Demo Dataset", use_container_width=True):
            demo_records = get_demo_records()
            validate_all(demo_records)
            existing_sources = {r.source_filename for r in st.session_state.records}
            added = 0
            for rec in demo_records:
                if rec.source_filename not in existing_sources:
                    st.session_state.records.append(rec)
                    added += 1
            if added:
                st.success(f"✅ Added {added} demo receipt(s)!")
            else:
                st.info("Demo records already loaded.")
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # File upload
    st.markdown("### Upload Your Receipt Images")
    uploaded_files = st.file_uploader(
        "Drop receipt images here",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="receipt_uploader",
        help="Upload PNG, JPG, or JPEG files. Maximum 10 MB each.",
    )

    if uploaded_files:
        new_files = [
            f for f in uploaded_files
            if f.name not in st.session_state.processed_files
        ]

        if not new_files:
            st.info("All uploaded files have already been processed.")
        else:
            st.markdown(f"**{len(new_files)} new file(s) ready to process:**")
            for f in new_files:
                size_kb = len(f.getvalue()) / 1024
                st.write(f"  • `{f.name}` — {size_kb:.1f} KB")

            if st.button(
                f"🔍 Extract Data from {len(new_files)} File(s)",
                use_container_width=True,
            ):
                progress = st.progress(0, text="Starting extraction…")
                new_records = []

                for idx, uploaded_file in enumerate(new_files):
                    progress.progress(
                        (idx) / len(new_files),
                        text=f"Processing {uploaded_file.name} ({idx + 1}/{len(new_files)})…",
                    )

                    # Validate file size
                    file_bytes = uploaded_file.getvalue()
                    if len(file_bytes) > cfg.max_upload_size_mb * 1024 * 1024:
                        st.warning(
                            f"⚠️ `{uploaded_file.name}` exceeds {cfg.max_upload_size_mb} MB. Skipped."
                        )
                        continue

                    try:
                        record, mode = extract_receipt(
                            image_bytes=file_bytes,
                            filename=uploaded_file.name,
                            api_key=cfg.gemini_api_key,
                            model_name=cfg.gemini_model,
                            file_index=idx + len(st.session_state.records),
                            timeout=cfg.ai_timeout_seconds,
                        )
                        validate_record(record)
                        new_records.append(record)
                        st.session_state.processed_files.add(uploaded_file.name)
                    except Exception as exc:
                        st.error(
                            f"❌ Failed to process `{uploaded_file.name}`: {exc}"
                        )

                progress.progress(1.0, text="Extraction complete!")

                if new_records:
                    # Validate all together for duplicate detection
                    validate_all(st.session_state.records + new_records)
                    st.session_state.records.extend(new_records)
                    mode_label = "AI 🤖" if cfg.gemini_api_key else "Mock/Demo 🎭"
                    st.success(
                        f"✅ Extracted {len(new_records)} record(s) using {mode_label} mode. "
                        "Go to **Review & Approve** to verify and approve expenses."
                    )
                    st.rerun()


# ─────────────────────────────────────────────
# PAGE: Review & Approve
# ─────────────────────────────────────────────

def page_review():
    st.markdown("## 🔍 Review & Approve Expenses")
    st.markdown(
        "Verify extracted data, correct errors, and approve expenses for inclusion in the report."
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    records = st.session_state.records

    if not records:
        st.markdown(
            '<div class="alert-info">No records to review. Upload receipts or load the demo dataset first.</div>',
            unsafe_allow_html=True,
        )
        return

    # Filter controls
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        filter_status = st.multiselect(
            "Filter by status",
            options=[s.value for s in ExpenseStatus],
            default=[s.value for s in ExpenseStatus],
            key="filter_status",
        )
    with col_f2:
        if st.button("🔄 Re-validate All Records", use_container_width=True):
            validate_all(st.session_state.records)
            st.success("Re-validation complete.")
            st.rerun()

    filtered = [r for r in records if r.status.value in filter_status]
    st.markdown(f"Showing **{len(filtered)}** of {len(records)} record(s)")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    for rec in filtered:
        # Determine card color accent
        accent = {
            ExpenseStatus.APPROVED: "#dcfce7",
            ExpenseStatus.PENDING: "#fef9c3",
            ExpenseStatus.NEEDS_CORRECTION: "#fee2e2",
            ExpenseStatus.REJECTED: "#f3f4f6",
        }.get(rec.status, "#f3f4f6")

        with st.expander(
            f"{'✅' if rec.is_approved else '⚠️' if rec.validation_issues else '📋'} "
            f"#{rec.id[:8]}  ·  {rec.vendor or 'Unknown Vendor'}  ·  {rec.amount_display}  ·  {rec.status.value}",
            expanded=(rec.status == ExpenseStatus.NEEDS_CORRECTION),
        ):
            # Validation issues banner
            if rec.validation_issues:
                for issue in rec.validation_issues:
                    css = "alert-error" if issue.severity == "error" else "alert-warning"
                    icon = "🔴" if issue.severity == "error" else "🟡"
                    st.markdown(
                        f'<div class="{css}">{icon} <b>{issue.field.title()}:</b> {issue.message}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown("")

            # Edit form
            with st.form(key=f"form_{rec.id}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_vendor = st.text_input(
                        "Vendor Name *", value=rec.vendor, key=f"vendor_{rec.id}"
                    )
                    new_date = st.date_input(
                        "Date *",
                        value=rec.date,
                        key=f"date_{rec.id}",
                        format="YYYY-MM-DD",
                    )
                with c2:
                    new_amount = st.text_input(
                        "Amount *",
                        value=str(rec.amount) if rec.amount is not None else "",
                        key=f"amount_{rec.id}",
                    )
                    new_currency = st.selectbox(
                        "Currency",
                        options=["INR", "USD", "EUR", "GBP", "Other"],
                        index=["INR", "USD", "EUR", "GBP", "Other"].index(rec.currency)
                        if rec.currency in ["INR", "USD", "EUR", "GBP"]
                        else 0,
                        key=f"currency_{rec.id}",
                    )
                with c3:
                    new_category = st.selectbox(
                        "Category",
                        options=[c.value for c in ExpenseCategory],
                        index=[c.value for c in ExpenseCategory].index(rec.category.value),
                        key=f"category_{rec.id}",
                    )
                    new_receipt_number = st.text_input(
                        "Receipt Number",
                        value=rec.receipt_number,
                        key=f"rcpt_{rec.id}",
                    )

                new_description = st.text_area(
                    "Description",
                    value=rec.description,
                    height=80,
                    key=f"desc_{rec.id}",
                )

                c_meta1, c_meta2 = st.columns(2)
                with c_meta1:
                    st.markdown(
                        f"**Source:** `{rec.source_filename}` &nbsp;|&nbsp; "
                        f"**Mode:** {_mode_badge(rec.extraction_mode)}",
                        unsafe_allow_html=True,
                    )
                with c_meta2:
                    new_notes = st.text_input(
                        "Notes (optional)", value=rec.notes, key=f"notes_{rec.id}"
                    )

                st.markdown("")
                b1, b2, b3, b4 = st.columns(4)
                save_btn = b1.form_submit_button("💾 Save Changes", use_container_width=True)
                approve_btn = b2.form_submit_button(
                    "✅ Approve", use_container_width=True, type="primary"
                )
                needs_btn = b3.form_submit_button("⚠️ Flag for Correction", use_container_width=True)
                reject_btn = b4.form_submit_button("❌ Reject", use_container_width=True)

                if save_btn or approve_btn or needs_btn or reject_btn:
                    # Apply edits
                    rec.vendor = new_vendor.strip()
                    rec.date = new_date
                    rec.amount = new_amount.strip() or None  # Let validator coerce
                    rec.currency = new_currency
                    rec.description = new_description.strip()
                    rec.category = new_category
                    rec.receipt_number = new_receipt_number.strip()
                    rec.notes = new_notes.strip()

                    # Re-validate
                    validate_record(rec)

                    if approve_btn:
                        if rec.has_errors:
                            st.error(
                                "⚠️ Cannot approve: this record has unresolved errors. "
                                "Please correct the highlighted fields first."
                            )
                        else:
                            rec.status = ExpenseStatus.APPROVED
                            _update_record(rec)
                            st.success("✅ Expense approved!")
                            st.rerun()
                    elif needs_btn:
                        rec.status = ExpenseStatus.NEEDS_CORRECTION
                        _update_record(rec)
                        st.warning("⚠️ Flagged for correction.")
                        st.rerun()
                    elif reject_btn:
                        rec.status = ExpenseStatus.REJECTED
                        _update_record(rec)
                        st.info("❌ Expense rejected.")
                        st.rerun()
                    else:  # save only
                        _update_record(rec)
                        st.success("Changes saved. Record re-validated.")
                        st.rerun()


# ─────────────────────────────────────────────
# PAGE: Generate Report
# ─────────────────────────────────────────────

def page_report():
    st.markdown("## 📄 Generate PDF Report")
    st.markdown(
        "Configure report details and download a professional expense report PDF."
    )
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    records = st.session_state.records

    if not records:
        st.markdown(
            '<div class="alert-info">No records loaded. Upload receipts or use the demo dataset first.</div>',
            unsafe_allow_html=True,
        )
        return

    summary = calculate_summary(records)

    # Summary preview
    st.markdown("### Report Preview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Records", summary.total_records)
    c2.metric("Approved", summary.approved_count)
    c3.metric("Pending / Needs Correction", summary.pending_count + summary.needs_correction_count)
    c4.metric("Rejected", summary.rejected_count)

    st.markdown("")
    st.metric("💰 Total Approved Expenditure", summary.total_approved_display)

    if summary.approved_count == 0:
        st.markdown(
            '<div class="alert-warning">⚠️ No approved records yet. '
            "Approve expenses in the <b>Review & Approve</b> tab before generating a report.</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Report configuration
    st.markdown("### Report Settings")
    col1, col2 = st.columns(2)
    with col1:
        org_name = st.text_input(
            "Organisation Name (optional)",
            placeholder="e.g. Seva Foundation India",
            key="rpt_org",
        )
        project_name = st.text_input(
            "Project Name (optional)",
            placeholder="e.g. Rural Health Camp 2024",
            key="rpt_project",
        )
    with col2:
        reporting_period = st.text_input(
            "Reporting Period (optional)",
            placeholder="e.g. October 2024",
            key="rpt_period",
        )
        include_narrative = st.checkbox(
            "Include narrative summary",
            value=True,
            key="rpt_narrative",
            help="AI-generated summary if API key is set, otherwise auto-generated from data.",
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Disclaimer
    st.markdown(
        '<div class="alert-warning">⚠️ <b>Disclaimer:</b> This report is a draft for internal '
        "review only. It has not been independently audited. Always verify figures with a "
        "qualified accountant before submitting to donors or regulatory bodies.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("")

    if st.button("📥 Generate & Download PDF Report", use_container_width=True, type="primary"):
        with st.spinner("Generating PDF report…"):
            try:
                narrative = ""
                if include_narrative:
                    narrative = generate_narrative_summary(
                        records,
                        summary,
                        api_key=cfg.gemini_api_key,
                        model_name=cfg.gemini_model,
                    )

                pdf_bytes = generate_pdf_report(
                    records=records,
                    summary=summary,
                    org_name=org_name,
                    project_name=project_name,
                    reporting_period=reporting_period,
                    narrative_summary=narrative,
                )

                from datetime import datetime  # noqa: PLC0415
                filename = f"janseva_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success(
                    f"✅ Report generated successfully! Click above to download `{filename}`."
                )
            except Exception as exc:
                st.error(f"❌ PDF generation failed: {exc}")
                raise


# ─────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────

page_map = {
    "🏠 Dashboard": page_dashboard,
    "📤 Upload Receipts": page_upload,
    "🔍 Review & Approve": page_review,
    "📄 Generate Report": page_report,
}

current_page = st.session_state.get("nav_radio", "🏠 Dashboard")
page_fn = page_map.get(current_page, page_dashboard)
page_fn()

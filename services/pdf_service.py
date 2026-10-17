"""
PDF generation service for JanSeva Impact Desk.
Uses ReportLab to produce a structured, downloadable expense report.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.expense import ExpenseRecord, ExpenseStatus
from services.report_service import ReportSummary, get_unresolved_records

# --------------------------------------------------------------------------- #
# Colour palette
# --------------------------------------------------------------------------- #
_PRIMARY = colors.HexColor("#1a6b3c")      # Forest green
_SECONDARY = colors.HexColor("#2d9a5e")    # Mid green
_ACCENT = colors.HexColor("#f0faf4")       # Very light green tint
_WARNING = colors.HexColor("#b45309")      # Amber
_ERROR = colors.HexColor("#dc2626")        # Red
_LIGHT_GRAY = colors.HexColor("#f3f4f6")
_MID_GRAY = colors.HexColor("#9ca3af")
_DARK = colors.HexColor("#111827")


# --------------------------------------------------------------------------- #
# Helper styles
# --------------------------------------------------------------------------- #

def _build_styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=_PRIMARY,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    subtitle = ParagraphStyle(
        "ReportSubtitle",
        fontName="Helvetica",
        fontSize=10,
        textColor=_MID_GRAY,
        spaceAfter=2,
        alignment=TA_CENTER,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=_PRIMARY,
        spaceBefore=12,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "BodyText",
        fontName="Helvetica",
        fontSize=9,
        textColor=_DARK,
        spaceAfter=3,
        leading=14,
    )
    small = ParagraphStyle(
        "SmallText",
        fontName="Helvetica",
        fontSize=8,
        textColor=_MID_GRAY,
        spaceAfter=2,
    )
    warning = ParagraphStyle(
        "WarningText",
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=_WARNING,
        spaceAfter=2,
    )
    metric_label = ParagraphStyle(
        "MetricLabel",
        fontName="Helvetica",
        fontSize=9,
        textColor=_MID_GRAY,
        alignment=TA_LEFT,
    )
    metric_value = ParagraphStyle(
        "MetricValue",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=_DARK,
        alignment=TA_LEFT,
    )
    return {
        "title": title,
        "subtitle": subtitle,
        "section_heading": section_heading,
        "body": body,
        "small": small,
        "warning": warning,
        "metric_label": metric_label,
        "metric_value": metric_value,
    }


# --------------------------------------------------------------------------- #
# PDF builder
# --------------------------------------------------------------------------- #

def generate_pdf_report(
    records: List[ExpenseRecord],
    summary: ReportSummary,
    org_name: str = "",
    project_name: str = "",
    reporting_period: str = "",
    narrative_summary: str = "",
) -> bytes:
    """
    Generate a PDF report and return raw bytes.

    Args:
        records: All expense records in session.
        summary: Pre-calculated ReportSummary.
        org_name: Optional organisation name.
        project_name: Optional project name.
        reporting_period: Optional reporting period string.
        narrative_summary: Optional AI/template-generated text summary.

    Returns:
        PDF file as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="JanSeva Impact Desk — Expense Report",
        author="JanSeva Impact Desk",
    )

    styles = _build_styles()
    story = []
    W = A4[0] - 40 * mm  # usable page width

    # ------------------------------------------------------------------ #
    # Header
    # ------------------------------------------------------------------ #
    story.append(Paragraph("JanSeva Impact Desk", styles["title"]))
    story.append(Paragraph("NGO Expense Report", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=_PRIMARY, spaceAfter=6))

    # Meta table
    meta_rows = [
        ["Generated on:", datetime.now().strftime("%d %B %Y, %I:%M %p")],
        ["Organisation:", org_name or "—"],
        ["Project:", project_name or "—"],
        ["Reporting Period:", reporting_period or "—"],
    ]
    meta_table = Table(meta_rows, colWidths=[40 * mm, W - 40 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), _MID_GRAY),
                ("TEXTCOLOR", (1, 0), (1, -1), _DARK),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    # ------------------------------------------------------------------ #
    # Summary metrics
    # ------------------------------------------------------------------ #
    story.append(Paragraph("Summary", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_SECONDARY, spaceAfter=4))

    col_w = W / 4
    metric_data = [
        [
            Paragraph("Total Records", styles["metric_label"]),
            Paragraph("Approved", styles["metric_label"]),
            Paragraph("Pending / Needs Correction", styles["metric_label"]),
            Paragraph("Rejected", styles["metric_label"]),
        ],
        [
            Paragraph(str(summary.total_records), styles["metric_value"]),
            Paragraph(str(summary.approved_count), styles["metric_value"]),
            Paragraph(
                str(summary.pending_count + summary.needs_correction_count),
                styles["metric_value"],
            ),
            Paragraph(str(summary.rejected_count), styles["metric_value"]),
        ],
    ]
    metric_table = Table(metric_data, colWidths=[col_w] * 4)
    metric_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _ACCENT),
                ("BOX", (0, 0), (-1, -1), 0.5, _SECONDARY),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(metric_table)
    story.append(Spacer(1, 4 * mm))

    # Total approved amount — highlighted box
    total_data = [
        [
            Paragraph("Total Approved Expenditure", styles["metric_label"]),
            Paragraph(summary.total_approved_display, styles["metric_value"]),
        ]
    ]
    total_table = Table(total_data, colWidths=[W * 0.6, W * 0.4])
    total_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    story.append(total_table)
    story.append(Spacer(1, 8 * mm))

    # ------------------------------------------------------------------ #
    # Narrative summary
    # ------------------------------------------------------------------ #
    if narrative_summary:
        story.append(Paragraph("Expense Summary", styles["section_heading"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_SECONDARY, spaceAfter=4))
        story.append(Paragraph(narrative_summary, styles["body"]))
        story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------ #
    # Approved expenses table
    # ------------------------------------------------------------------ #
    approved = [r for r in records if r.status == ExpenseStatus.APPROVED]
    story.append(Paragraph("Approved Expenses", styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_SECONDARY, spaceAfter=4))

    if approved:
        col_widths = [22 * mm, 38 * mm, 50 * mm, 32 * mm, 28 * mm, 26 * mm]
        expense_header = [
            Paragraph("<b>Date</b>", styles["small"]),
            Paragraph("<b>Vendor</b>", styles["small"]),
            Paragraph("<b>Description</b>", styles["small"]),
            Paragraph("<b>Category</b>", styles["small"]),
            Paragraph("<b>Amount</b>", styles["small"]),
            Paragraph("<b>Source</b>", styles["small"]),
        ]
        expense_rows = [expense_header]

        for rec in approved:
            expense_rows.append(
                [
                    Paragraph(rec.date_display, styles["small"]),
                    Paragraph(rec.vendor or "—", styles["small"]),
                    Paragraph((rec.description or "—")[:80], styles["small"]),
                    Paragraph(rec.category.value, styles["small"]),
                    Paragraph(rec.amount_display, styles["small"]),
                    Paragraph((rec.source_filename or "—")[:25], styles["small"]),
                ]
            )

        expense_table = Table(expense_rows, colWidths=col_widths, repeatRows=1)
        expense_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_GRAY]),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _MID_GRAY),
                    ("BOX", (0, 0), (-1, -1), 0.5, _MID_GRAY),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(expense_table)
    else:
        story.append(
            Paragraph("No approved expense records to display.", styles["body"])
        )

    story.append(Spacer(1, 8 * mm))

    # ------------------------------------------------------------------ #
    # Unresolved issues
    # ------------------------------------------------------------------ #
    unresolved = get_unresolved_records(records)
    rejected = [r for r in records if r.status == ExpenseStatus.REJECTED]

    if unresolved or rejected:
        story.append(Paragraph("Excluded & Unresolved Records", styles["section_heading"]))
        story.append(
            HRFlowable(width="100%", thickness=0.5, color=_WARNING, spaceAfter=4)
        )
        story.append(
            Paragraph(
                "The following records were excluded from the approved total because "
                "they are pending review, require correction, or were rejected.",
                styles["body"],
            )
        )
        story.append(Spacer(1, 2 * mm))

        for rec in unresolved + rejected:
            issues_text = "; ".join(i.message for i in rec.validation_issues) or "No specific issues recorded."
            row_text = (
                f"<b>#{rec.id[:8]}</b> — {rec.vendor or 'Unknown Vendor'} | "
                f"{rec.date_display} | {rec.amount_display} | Status: {rec.status.value}<br/>"
                f"<i>Issues: {issues_text}</i>"
            )
            story.append(Paragraph(row_text, styles["warning"]))
            story.append(Spacer(1, 1 * mm))

        story.append(Spacer(1, 4 * mm))

    # ------------------------------------------------------------------ #
    # Disclaimer
    # ------------------------------------------------------------------ #
    story.append(HRFlowable(width="100%", thickness=1, color=_MID_GRAY, spaceAfter=4))
    disclaimer = (
        "<b>DRAFT REPORT — NOT FOR OFFICIAL SUBMISSION WITHOUT REVIEW</b><br/>"
        "This report was generated by JanSeva Impact Desk, an AI-assisted expense "
        "management tool. The data in this report reflects information entered and "
        "approved by authorised staff. This report has NOT been independently audited. "
        "All figures should be verified by a qualified accountant before submission to "
        "donors, regulators, or government bodies. AI-extracted data may contain errors; "
        "human review and approval are required before any record is included in this report."
    )
    story.append(Paragraph(disclaimer, styles["small"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def generate_narrative_summary(
    records: List[ExpenseRecord],
    summary: ReportSummary,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.8-flash",
) -> str:
    """
    Generate a narrative summary of approved expenses.
    Uses Gemini if available, otherwise falls back to a deterministic template.
    """
    from models.expense import ExpenseStatus  # noqa: PLC0415

    approved = [r for r in records if r.status == ExpenseStatus.APPROVED]

    if api_key and approved:
        try:
            return _ai_narrative(approved, summary, api_key, model_name)
        except Exception as exc:  # noqa: BLE001
            pass  # Fall through to template

    return _template_narrative(approved, summary)


def _template_narrative(
    approved: List[ExpenseRecord], summary: ReportSummary
) -> str:
    """Deterministic narrative template when AI is unavailable."""
    if not approved:
        return "No expenses have been approved for this reporting period."

    # Category breakdown
    from collections import Counter  # noqa: PLC0415
    cat_counts = Counter(r.category.value for r in approved)
    top_cats = cat_counts.most_common(3)
    cat_text = ", ".join(f"{cat} ({count} record{'s' if count > 1 else ''})" for cat, count in top_cats)

    return (
        f"This report covers {summary.approved_count} approved expense record(s) with a "
        f"total approved expenditure of {summary.total_approved_display}. "
        f"The primary expense categories are: {cat_text}. "
        f"All records included in this report have been reviewed and approved by "
        f"authorised staff. {summary.pending_count + summary.needs_correction_count} "
        f"record(s) remain pending review and are excluded from this total."
    )


def _ai_narrative(
    approved: List[ExpenseRecord],
    summary: ReportSummary,
    api_key: str,
    model_name: str,
) -> str:
    """Generate a narrative summary using Gemini."""
    import google.generativeai as genai  # noqa: PLC0415

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    records_text = "\n".join(
        f"- {r.date_display}: {r.vendor} | {r.category.value} | {r.amount_display} | {r.description}"
        for r in approved
    )

    prompt = (
        f"Write a concise, professional 3-4 sentence narrative summary for an NGO "
        f"expense report. Base it ONLY on the following verified, approved expense data:\n\n"
        f"{records_text}\n\n"
        f"Total approved expenditure: {summary.total_approved_display}\n\n"
        f"Do not add any information not present in the data above. "
        f"Do not make up impact figures. Write in formal English."
    )

    response = model.generate_content(prompt)
    return response.text.strip()
